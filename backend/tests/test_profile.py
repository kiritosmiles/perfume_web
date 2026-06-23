"""Tests for user profile service (F1: FR-1.1, FR-1.3)."""

import uuid

import pytest
from app.core.pg import get_pg_pool
from app.services.profile import (
    ensure_profile_exists,
    get_user_profile,
    increment_conversation_count,
    update_emotion_tendency,
    submit_onboarding,
    should_extract_full_profile,
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
