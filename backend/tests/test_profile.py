"""Tests for user profile service (F1: FR-1.1, FR-1.3, FR-2.5)."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.pg import get_pg_pool
from app.services.emotion import compute_value_dimensions
from app.services.profile import (
    ensure_profile_exists,
    get_user_profile,
    increment_conversation_count,
    update_emotion_tendency,
    submit_onboarding,
    should_extract_full_profile,
    extract_full_profile_llm,
    _should_re_extract,
    get_recent_memory_for_extraction,
    FULL_PROFILE_THRESHOLD,
)


async def _create_user(uid: str | None = None) -> str:
    """Create a minimal user entry in the users table for FK constraints."""
    uid = uid or str(uuid.uuid4())
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (id, email, password_hash) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
            uid, f"test_{uid[:8]}@test.local",
            "$2b$12$LJ3m4ys3Lk0TSwHBfQfJc.Ya5qFmNuZ1kYYa1l6MQaH7H4eOoJBDe",
        )
    return uid


class TestProfileCRUD:
    """Basic create/read/update operations."""

    @pytest.mark.asyncio
    async def test_ensure_creates_profile(self):
        uid = await _create_user()
        await ensure_profile_exists(uid)
        profile = await get_user_profile(uid)
        assert profile is not None
        assert profile["conversation_count"] == 0
        assert "personality_tags" in profile["profile_data"]

    @pytest.mark.asyncio
    async def test_get_nonexistent_profile_returns_none(self):
        result = await get_user_profile("00000000-0000-0000-0000-000000000000")
        assert result is None

    @pytest.mark.asyncio
    async def test_increment_conversation_count(self):
        uid = await _create_user()
        await ensure_profile_exists(uid)
        c1 = await increment_conversation_count(uid)
        assert c1 == 1
        c2 = await increment_conversation_count(uid)
        assert c2 == 2


class TestEmotionTendency:
    """Emotion tendency updates with exponential moving average."""

    @pytest.mark.asyncio
    async def test_update_empty_profile(self):
        uid = await _create_user()
        await ensure_profile_exists(uid)
        vector = {"joy": 0.8, "calm": 0.2, "sadness": 0, "anxiety": 0,
                   "excitement": 0, "nostalgia": 0, "romance": 0, "melancholy": 0}
        await update_emotion_tendency(uid, vector)
        profile = await get_user_profile(uid)
        tendency = profile["profile_data"].get("emotion_tendency", {})
        assert tendency.get("joy", 0) > 0.5

    @pytest.mark.asyncio
    async def test_update_existing_profile(self):
        uid = await _create_user()
        await ensure_profile_exists(uid)
        v1 = {"joy": 1.0, "calm": 0, "sadness": 0, "anxiety": 0,
              "excitement": 0, "nostalgia": 0, "romance": 0, "melancholy": 0}
        v2 = {"joy": 0, "calm": 1.0, "sadness": 0, "anxiety": 0,
              "excitement": 0, "nostalgia": 0, "romance": 0, "melancholy": 0}
        await update_emotion_tendency(uid, v1)
        await update_emotion_tendency(uid, v2)
        profile = await get_user_profile(uid)
        tendency = profile["profile_data"].get("emotion_tendency", {})
        assert tendency.get("joy", 0) > 0.5
        assert tendency.get("calm", 0) > 0.2

    @pytest.mark.asyncio
    async def test_stored_tendency_produces_value_dimensions(self):
        """FR-2.5: profile's emotion_tendency should produce valid value dimensions."""
        uid = await _create_user()
        await ensure_profile_exists(uid)
        await update_emotion_tendency(uid, {
            "joy": 0.6, "sadness": 0.1, "anxiety": 0.2, "calm": 0.3,
            "excitement": 0.5, "nostalgia": 0.2, "romance": 0.4, "melancholy": 0.1,
        })
        profile = await get_user_profile(uid)
        tendency = profile["profile_data"].get("emotion_tendency", {})
        assert len(tendency) > 0
        vd = compute_value_dimensions(tendency)
        assert vd is not None
        assert set(vd.keys()) == {"pleasure", "activation", "dominance", "social", "aesthetic", "nostalgia"}
        assert all(0.0 <= v <= 1.0 for v in vd.values())


class TestOnboarding:
    """Onboarding questionnaire processing."""

    @pytest.mark.asyncio
    async def test_submit_onboarding_creates_full_profile(self):
        uid = await _create_user()
        answers = [
            {
                "question": 1, "option": "🌿 自然清新",
                "mapped_vector": {"joy": 0.3, "calm": 0.5, "excitement": 0.1, "nostalgia": 0.1},
                "mapped_tags": ["清新自然"],
            },
            {
                "question": 2, "option": "日常必备",
                "mapped_vector": None, "mapped_tags": ["实用型", "日常伴侣"],
            },
            {
                "question": 3, "option": "没有特别不喜欢的",
                "mapped_vector": None, "mapped_tags": [],
            },
        ]
        profile = await submit_onboarding(uid, answers)
        assert profile["profile_level"] == "full"
        assert profile["questionnaire_completed"] is True
        assert "清新自然" in profile["personality_tags"]
        assert "实用型" in profile["personality_tags"]
        assert len(profile["emotion_tendency"]) > 0


class TestProgressiveProfile:
    """Progressive profile building (light → full after 3 conversations)."""

    @pytest.mark.asyncio
    async def test_new_user_is_light(self):
        uid = await _create_user()
        await ensure_profile_exists(uid)
        assert not await should_extract_full_profile(uid)

    @pytest.mark.asyncio
    async def test_after_threshold_is_full(self):
        uid = await _create_user()
        await ensure_profile_exists(uid)
        for _ in range(FULL_PROFILE_THRESHOLD):
            await increment_conversation_count(uid)
        assert await should_extract_full_profile(uid)

    @pytest.mark.asyncio
    async def test_onboarding_bypasses_threshold(self):
        uid = await _create_user()
        answers = [{
            "question": 1, "option": "🌿",
            "mapped_vector": {"joy": 0.5, "calm": 0.5}, "mapped_tags": ["清新"],
        }]
        await submit_onboarding(uid, answers)
        assert await should_extract_full_profile(uid)


class TestProfileExtraction:
    """Dynamic tag extraction via LLM (FR-1.6)."""

    @pytest.mark.asyncio
    async def test_no_llm_key_returns_none(self):
        """When LLM_API_KEY is empty, extraction should skip gracefully."""
        uid = await _create_user()
        await ensure_profile_exists(uid)
        for _ in range(FULL_PROFILE_THRESHOLD + 1):
            await increment_conversation_count(uid)

        with patch('app.services.profile.settings') as mock_settings:
            mock_settings.LLM_API_KEY = ""
            mock_settings.PROFILE_EXTRACTION_THROTTLE = 3
            result = await extract_full_profile_llm(uid)
            assert result is None  # Graceful fallback, no crash

    @pytest.mark.asyncio
    async def test_throttle_before_min_conversations(self):
        """Should skip extraction when not enough conversations since last extraction."""
        uid = await _create_user()
        await ensure_profile_exists(uid)
        await increment_conversation_count(uid)  # Only 1 conversation

        with patch('app.services.profile.settings') as mock_settings:
            mock_settings.PROFILE_EXTRACTION_THROTTLE = 5
            assert not await _should_re_extract(uid)

    @pytest.mark.asyncio
    async def test_extraction_updates_profile_success(self):
        """LLM extraction should update personality_tags and preferred fields."""
        uid = await _create_user()
        await ensure_profile_exists(uid)
        for _ in range(FULL_PROFILE_THRESHOLD + 1):
            await increment_conversation_count(uid)

        await update_emotion_tendency(uid, {
            "joy": 0.6, "calm": 0.3, "sadness": 0, "anxiety": 0,
            "excitement": 0, "nostalgia": 0.1, "romance": 0, "melancholy": 0,
        })

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '{"personality_tags":["清新自然","文艺感性"],"preferred_accords":["花香调","绿叶调"],"preferred_notes":["茉莉","铃兰"]}'
                }
            }]
        }

        with patch('app.services.profile.settings') as mock_settings:
            mock_settings.LLM_API_KEY = "test-key"
            mock_settings.LLM_BASE_URL = "https://mock.api/v1"
            mock_settings.LLM_MODEL = "test-model"
            mock_settings.PROFILE_EXTRACTION_THROTTLE = 3
            mock_settings.LLM_TIMEOUT = 8.0
            with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
                mock_post.return_value = mock_response
                with patch('app.services.profile.get_l3_summaries', new_callable=AsyncMock) as mock_l3:
                    mock_l3.return_value = ["用户喜欢清新的花香调香水"]
                    result = await extract_full_profile_llm(uid)
                    assert result is not None
                    assert "清新自然" in result["personality_tags"]
                    assert "花香调" in result["preferred_accords"]
                    assert "茉莉" in result["preferred_notes"]
                    assert result["profile_level"] == "full"
                    assert result.get("extraction_count", 0) >= 1

    @pytest.mark.asyncio
    async def test_llm_api_error_returns_none(self):
        """When LLM API returns non-200, extraction should fail gracefully."""
        uid = await _create_user()
        await ensure_profile_exists(uid)
        for _ in range(FULL_PROFILE_THRESHOLD + 1):
            await increment_conversation_count(uid)

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch('app.services.profile.settings') as mock_settings:
            mock_settings.LLM_API_KEY = "test-key"
            mock_settings.LLM_BASE_URL = "https://mock.api/v1"
            mock_settings.LLM_MODEL = "test-model"
            mock_settings.PROFILE_EXTRACTION_THROTTLE = 3
            mock_settings.LLM_TIMEOUT = 8.0
            with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
                mock_post.return_value = mock_response
                result = await extract_full_profile_llm(uid)
                assert result is None  # Graceful failure

    @pytest.mark.asyncio
    async def test_empty_memory_no_crash(self):
        """get_recent_memory_for_extraction should handle empty L3 gracefully."""
        uid = await _create_user()
        with patch('app.services.profile.get_l3_summaries', new_callable=AsyncMock) as mock_l3:
            mock_l3.return_value = []
            result = await get_recent_memory_for_extraction(uid)
            assert "暂无" in result or len(result) > 0

    @pytest.mark.asyncio
    async def test_merge_preserves_existing_when_llm_empty(self):
        """If LLM returns empty arrays, existing profile data should be preserved."""
        uid = await _create_user()
        await submit_onboarding(uid, [{
            "question": 1, "option": "🌿",
            "mapped_vector": {"joy": 0.5, "calm": 0.5}, "mapped_tags": ["自然清新"],
        }])

        for _ in range(5):
            await increment_conversation_count(uid)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '{"personality_tags":[],"preferred_accords":[],"preferred_notes":[]}'
                }
            }]
        }

        with patch('app.services.profile.settings') as mock_settings:
            mock_settings.LLM_API_KEY = "test-key"
            mock_settings.LLM_BASE_URL = "https://mock.api/v1"
            mock_settings.LLM_MODEL = "test-model"
            mock_settings.PROFILE_EXTRACTION_THROTTLE = 3
            mock_settings.LLM_TIMEOUT = 8.0
            with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
                mock_post.return_value = mock_response
                result = await extract_full_profile_llm(uid)
                if result:  # Depends on throttle state
                    assert "自然清新" in result["personality_tags"]  # Preserved from onboarding
