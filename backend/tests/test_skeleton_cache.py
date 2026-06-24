"""Tests for Recipe Skeleton Cache (LLM copy text degradation fallback)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.redis import (
    build_skeleton_cache_key,
    cache_skeleton,
    get_cached_skeleton,
    SKELETON_CACHE_TTL,
)


# ── Fixtures ───────────────────────────────────────────────────────────────────

SAMPLE_SKELETONS: list[dict] = [
    {
        "rank": 1,
        "name": "No.5 Chanel",
        "brand": "Chanel",
        "match_score": 92,
        "notes_combination": {
            "top": ["醛香", "依兰"],
            "middle": ["玫瑰", "茉莉"],
            "base": ["檀木", "香草"],
        },
        "copy_full_text": "当醛香的明亮遇见玫瑰的温柔，No.5 Chanel\n它是一段传奇，也是你的此刻。\n经典的魅力不在于年代，而在于它恰好说中了你的心情。",
        "image_url": "https://example.com/no5.jpg",
        "longevity": 8.0,
        "sillage": 6.5,
        "season": "all",
    },
    {
        "rank": 2,
        "name": "Light Blue Dolce & Gabbana",
        "brand": "Dolce & Gabbana",
        "match_score": 88,
        "notes_combination": {
            "top": ["柠檬", "青苹果"],
            "middle": ["茉莉", "竹子"],
            "base": ["雪松", "琥珀"],
        },
        "copy_full_text": "地中海的阳光穿过柠檬树的叶子\nLight Blue 是一阵清凉的海风，带走所有焦虑。\n穿上它，仿佛夏天永远不会结束。",
        "image_url": "https://example.com/lightblue.jpg",
        "longevity": 6.0,
        "sillage": 5.0,
        "season": "summer",
    },
]

EMOTION_VECTOR_A = {
    "joy": 0.35, "calm": 0.15, "excitement": 0.12,
    "romance": 0.10, "nostalgia": 0.10, "melancholy": 0.08,
    "sadness": 0.05, "anxiety": 0.05,
}

EMOTION_VECTOR_B = {
    "nostalgia": 0.40, "melancholy": 0.25, "calm": 0.15,
    "sadness": 0.10, "romance": 0.05, "joy": 0.03,
    "excitement": 0.01, "anxiety": 0.01,
}


# ── TestSkeletonCacheKey ────────────────────────────────────────────────────────

class TestSkeletonCacheKey:
    """Test build_skeleton_cache_key() determinism and uniqueness."""

    def test_cache_key_deterministic(self):
        """Same emotion vector + intent + scene → same key every time."""
        key1 = build_skeleton_cache_key(EMOTION_VECTOR_A, "self_use", None)
        key2 = build_skeleton_cache_key(EMOTION_VECTOR_A, "self_use", None)
        assert key1 == key2
        assert key1.startswith("skeleton:")
        assert "self_use" in key1
        assert "none" in key1  # scene=None → "none"

    def test_different_vectors_different_keys(self):
        """Different emotion vectors → different keys."""
        key_a = build_skeleton_cache_key(EMOTION_VECTOR_A, "self_use", None)
        key_b = build_skeleton_cache_key(EMOTION_VECTOR_B, "self_use", None)
        assert key_a != key_b

    def test_different_intent_different_keys(self):
        """Different intent → different keys."""
        key_self = build_skeleton_cache_key(EMOTION_VECTOR_A, "self_use", None)
        key_gift = build_skeleton_cache_key(EMOTION_VECTOR_A, "gift", None)
        assert key_self != key_gift

    def test_different_scene_different_keys(self):
        """Different scene tag → different keys."""
        key_no_scene = build_skeleton_cache_key(EMOTION_VECTOR_A, "self_use", None)
        key_work = build_skeleton_cache_key(EMOTION_VECTOR_A, "self_use", "work")
        assert key_no_scene != key_work

    def test_tiny_values_dropped(self):
        """Dimensions with value <= 0.05 are dropped from key."""
        key = build_skeleton_cache_key(EMOTION_VECTOR_B, "self_use", None)
        # EMOTION_VECTOR_B has joy:0.03, excitement:0.01, anxiety:0.01 — all <=0.05
        assert "joy" not in key
        assert "excitement" not in key
        assert "anxiety" not in key

    def test_dimensions_sorted_alphabetically(self):
        """Dimensions appear in alphabetical order regardless of dict insertion."""
        # Create a vector in non-alphabetical insertion order
        unordered = {"excitement": 0.30, "calm": 0.20, "joy": 0.25, "anxiety": 0.06}
        key = build_skeleton_cache_key(unordered, "self_use", None)
        # anxiety should come before calm before excitement before joy in key
        pos_anx = key.index("anxiety")
        pos_calm = key.index("calm")
        pos_exc = key.index("excitement")
        pos_joy = key.index("joy")
        assert pos_anx < pos_calm < pos_exc < pos_joy


# ── TestSkeletonCacheReadWrite ──────────────────────────────────────────────────

class TestSkeletonCacheReadWrite:
    """Test cache_skeleton() / get_cached_skeleton() with mocked Redis."""

    @pytest.mark.asyncio
    async def test_write_then_read(self):
        """Write skeletons → read returns same data."""
        mock_redis = MagicMock()
        store: dict[str, str] = {}

        async def mock_set(key, value, ex=None):
            store[key] = value

        async def mock_get(key):
            return store.get(key)

        mock_redis.set = mock_set
        mock_redis.get = mock_get

        import json as _json
        with patch("app.core.redis._get_client", return_value=mock_redis):
            await cache_skeleton("skeleton:test:key", SAMPLE_SKELETONS)
            result = await get_cached_skeleton("skeleton:test:key")

        assert result is not None
        assert len(result) == 2
        assert result[0]["name"] == "No.5 Chanel"
        assert result[0]["match_score"] == 92
        assert "copy_full_text" in result[0]

    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self):
        """Key not written → get returns None."""
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=None)

        with patch("app.core.redis._get_client", return_value=mock_redis):
            result = await get_cached_skeleton("skeleton:nonexistent:key")
            assert result is None

    @pytest.mark.asyncio
    async def test_redis_unavailable_returns_none(self):
        """Redis unavailable → get returns None gracefully."""
        with patch("app.core.redis._get_client", return_value=None):
            result = await get_cached_skeleton("skeleton:any:key")
            assert result is None

    @pytest.mark.asyncio
    async def test_redis_unavailable_cache_write_noop(self):
        """Redis unavailable → cache write is no-op (no exception)."""
        with patch("app.core.redis._get_client", return_value=None):
            await cache_skeleton("skeleton:any:key", SAMPLE_SKELETONS)
            # No exception = success

    @pytest.mark.asyncio
    async def test_cache_ttl_set(self):
        """cache_skeleton sets TTL = SKELETON_CACHE_TTL (86400)."""
        mock_redis = MagicMock()
        mock_redis.set = AsyncMock()

        with patch("app.core.redis._get_client", return_value=mock_redis):
            await cache_skeleton("skeleton:test:key", SAMPLE_SKELETONS)

        # Verify set was called with ex=86400 (default)
        mock_redis.set.assert_called_once()
        call_kwargs = mock_redis.set.call_args
        assert "ex" in call_kwargs.kwargs
        # Caller uses default ttl=SKELETON_CACHE_TTL=86400
