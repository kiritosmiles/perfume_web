"""Tests for emotion journal service and API (F4: FR-4.9)."""

import json as _json
import uuid
from datetime import date, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.pg import get_pg_pool
from app.services.journal import (
    get_emotion_trend,
    get_weekly_journal,
    _extract_emotion_from_text,
    _primary_emotion,
    _fallback_narrative,
)


async def _create_user(uid: str | None = None) -> tuple[str, str]:
    """Create a user and return (user_id, access_token)."""
    uid = uid or str(uuid.uuid4())
    email = f"test_{uid[:8]}@journal.local"
    password = "testpass123"
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (id, email, password_hash) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
            uid, email,
            "$2b$12$LJ3m4ys3Lk0TSwHBfQfJc.Ya5qFmNuZ1kYYa1l6MQaH7H4eOoJBDe",
        )

    # Get a token
    from app.core.auth import create_access_token
    token = create_access_token(uid)
    return uid, token


async def _insert_l3_entry(
    user_id: str,
    day_offset: int = 0,
    text: str = "",
    keywords: list[str] | None = None,
    emotion_summary: dict | None = None,
):
    """Insert a test L3 memory entry."""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        d = date.today() - timedelta(days=day_offset)
        await conn.execute(
            """INSERT INTO memory_l3 (user_id, date, text, preference_keywords, emotion_summary)
               VALUES ($1::uuid, $2::date, $3, $4, $5::jsonb)
               ON CONFLICT (user_id, date) DO UPDATE
               SET text = $3, preference_keywords = $4, emotion_summary = $5::jsonb""",
            user_id, d,
            text or f"情绪日记 day {day_offset}",
            keywords or [],
            _json.dumps(emotion_summary or {}),
        )


class TestEmotionExtraction:
    """Unit tests for keyword-based emotion extraction from text."""

    def test_extract_joy_from_text(self):
        scores = _extract_emotion_from_text("今天很开心，感到非常喜悦和快乐")
        assert scores.get("joy", 0) > 0

    def test_extract_sadness_from_text(self):
        scores = _extract_emotion_from_text("心情有些低落和难过，忍不住哭了")
        assert scores.get("sadness", 0) > 0

    def test_extract_mixed_emotions(self):
        scores = _extract_emotion_from_text("既兴奋又有点紧张，不过整体很浪漫")
        assert scores.get("excitement", 0) > 0
        assert scores.get("anxiety", 0) > 0
        assert scores.get("romance", 0) > 0

    def test_extract_no_emotion(self):
        scores = _extract_emotion_from_text("今天去超市买了东西")
        assert len(scores) == 0

    def test_primary_emotion(self):
        scores = {"joy": 0.67, "calm": 0.33, "excitement": 0.33}
        assert _primary_emotion(scores) == "joy"

    def test_primary_emotion_none(self):
        assert _primary_emotion({}) is None


class TestFallbackNarrative:
    """Template-based fallback narratives."""

    def test_fallback_with_data(self):
        week = {
            "primary_emotion": "joy",
            "emotion_vector": {"joy": 0.7, "calm": 0.3},
            "top_keywords": ["佛手柑", "茉莉"],
            "session_count": 3,
            "days": [{"date": "2026-06-15", "primary_emotion": "joy"}],
        }
        narrative = _fallback_narrative(week)
        assert "喜悦" in narrative or "joy" in narrative
        assert "3" in narrative
        assert len(narrative) > 30

    def test_fallback_none(self):
        narrative = _fallback_narrative(None)
        assert "暂无" in narrative


class TestEmotionTrend:
    """Emotion trend queries from L3 memory."""

    @pytest.mark.asyncio
    async def test_trend_empty_for_new_user(self):
        uid, _ = await _create_user()
        trend = await get_emotion_trend(uid, days=30)
        assert trend == []

    @pytest.mark.asyncio
    async def test_trend_with_data(self):
        uid, _ = await _create_user()
        await _insert_l3_entry(uid, day_offset=1,
                               text="今天很开心，喜欢柑橘调的清新感觉",
                               keywords=["柑橘", "清新"],
                               emotion_summary={"joy": 0.8, "calm": 0.2})
        await _insert_l3_entry(uid, day_offset=2,
                               text="有些焦虑的一天，木质调让人平静",
                               keywords=["木质", "平静"],
                               emotion_summary={"anxiety": 0.7, "calm": 0.3})

        trend = await get_emotion_trend(uid, days=7)
        assert len(trend) == 2
        # Ordered by date ascending (older first)
        assert trend[0]["primary_emotion"] is not None
        assert trend[1]["primary_emotion"] is not None
        assert len(trend[0]["keywords"]) >= 1

    @pytest.mark.asyncio
    async def test_trend_uses_stored_emotion_summary(self):
        uid, _ = await _create_user()
        await _insert_l3_entry(uid, day_offset=0,
                               text="random text without emotion keywords",
                               keywords=[],
                               emotion_summary={"joy": 0.9})

        trend = await get_emotion_trend(uid, days=7)
        assert len(trend) == 1
        # Should use stored emotion_summary (joy=0.9) rather than text extraction
        assert trend[0]["primary_emotion"] == "joy"


class TestWeeklyJournal:
    """Weekly journal generation."""

    @pytest.mark.asyncio
    async def test_journal_empty_for_new_user(self):
        uid, _ = await _create_user()
        journal = await get_weekly_journal(uid)
        assert journal["this_week"] is None
        assert journal["last_week"] is None
        assert "暂无" in journal["narrative"]

    @pytest.mark.asyncio
    async def test_journal_with_data(self):
        uid, _ = await _create_user()
        # Insert entries for this past week
        for i in range(1, 4):
            await _insert_l3_entry(uid, day_offset=i,
                                   text=f"day {i}: 心情不错，喜欢花香",
                                   keywords=["花香", "茉莉"],
                                   emotion_summary={"joy": 0.7, "calm": 0.3})

        journal = await get_weekly_journal(uid)
        assert journal["this_week"] is not None
        assert journal["this_week"]["session_count"] >= 1
        assert len(journal["narrative"]) > 20

    @pytest.mark.asyncio
    async def test_journal_with_specific_week(self):
        uid, _ = await _create_user()
        # Insert an entry for a known past Monday
        today = date.today()
        monday = today - timedelta(days=today.weekday() + 14)  # 2 weeks ago

        await _insert_l3_entry(uid, day_offset=(today - monday).days,
                               text="怀旧的一天，想到了很多过去的事",
                               keywords=["怀旧", "木质"],
                               emotion_summary={"nostalgia": 0.8, "melancholy": 0.2})

        journal = await get_weekly_journal(uid, week_start=monday.isoformat())
        assert journal["week_start"] == monday.isoformat()
        assert journal["this_week"] is not None


class TestJournalAPI:
    """Integration tests for journal API endpoints."""

    @pytest.mark.asyncio
    async def test_get_trend_api(self):
        uid, token = await _create_user()
        await _insert_l3_entry(uid, day_offset=0,
                               text="开心 test",
                               keywords=["柑橘"],
                               emotion_summary={"joy": 0.8})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/journal/trend?days=7",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["days"] == 7
        assert body["count"] >= 1

    @pytest.mark.asyncio
    async def test_get_weekly_api(self):
        uid, token = await _create_user()
        await _insert_l3_entry(uid, day_offset=1,
                               text="平静的一天",
                               keywords=["清新"],
                               emotion_summary={"calm": 0.9})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/journal/weekly",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert "week_start" in body
        assert "narrative" in body

    @pytest.mark.asyncio
    async def test_trend_requires_auth(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/journal/trend")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_weekly_requires_auth(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/journal/weekly")
        assert resp.status_code == 401
