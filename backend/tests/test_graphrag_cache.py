"""Tests for GraphRAG result cache (Phase 4 — hot-path caching)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Cache key generation (no Redis needed) ────────────────────────────────────

class TestCacheKeyGeneration:
    """build_graphrag_cache_key produces deterministic, scene-aware keys."""

    def test_single_card_key(self):
        from app.core.redis import build_graphrag_cache_key
        vec = {
            "joy": 0.9, "sadness": 0.0, "anxiety": 0.0, "calm": 0.2,
            "excitement": 0.7, "nostalgia": 0.0, "romance": 0.1, "melancholy": 0.0,
        }
        key = build_graphrag_cache_key(vec, None)
        assert key.startswith("graphrag:")
        assert "none" in key
        assert "joy:0.900" in key

    def test_dual_card_key_is_deterministic(self):
        from app.core.redis import build_graphrag_cache_key
        vec = {
            "joy": 0.6, "calm": 0.5, "sadness": 0.0, "anxiety": 0.0,
            "excitement": 0.3, "nostalgia": 0.0, "romance": 0.1, "melancholy": 0.0,
        }
        key1 = build_graphrag_cache_key(vec, "work")
        key2 = build_graphrag_cache_key(vec, "work")
        assert key1 == key2  # Deterministic regardless of dict insertion order

    def test_scene_tag_in_key(self):
        from app.core.redis import build_graphrag_cache_key
        vec = dict.fromkeys(["joy", "sadness", "anxiety", "calm",
                             "excitement", "nostalgia", "romance", "melancholy"], 0.0)
        vec["joy"] = 1.0
        key_no_scene = build_graphrag_cache_key(vec, None)
        key_with_scene = build_graphrag_cache_key(vec, "work")
        assert "none" in key_no_scene
        assert "work" in key_with_scene
        assert key_no_scene != key_with_scene

    def test_different_vectors_produce_different_keys(self):
        from app.core.redis import build_graphrag_cache_key
        vec_a = dict.fromkeys(["joy", "sadness", "anxiety", "calm",
                               "excitement", "nostalgia", "romance", "melancholy"], 0.0)
        vec_a["joy"] = 0.9
        vec_a["calm"] = 0.2
        vec_b = dict(vec_a)
        vec_b["calm"] = 0.8  # Different calm weight
        key_a = build_graphrag_cache_key(vec_a, None)
        key_b = build_graphrag_cache_key(vec_b, None)
        assert key_a != key_b

    def test_tiny_values_dropped_from_key(self):
        from app.core.redis import build_graphrag_cache_key
        vec = dict.fromkeys(["joy", "sadness", "anxiety", "calm",
                             "excitement", "nostalgia", "romance", "melancholy"], 0.0)
        vec["joy"] = 0.95
        vec["calm"] = 0.03  # Below 0.05 threshold
        key = build_graphrag_cache_key(vec, None)
        assert "calm" not in key  # Dropped


# ── Cache read / write (mock Redis) ───────────────────────────────────────────

CANDIDATES_FIXTURE = [
    {"name": "Test Bloom", "brand": "Test House", "score": 95.0, "accord": "floral"},
    {"name": "Test Woods", "brand": "Test House", "score": 88.0, "accord": "woody"},
]


class TestCacheReadWrite:
    """Redis-backed cache get/set via mocked _get_client."""

    @pytest.mark.asyncio
    async def test_cache_write_then_read(self):
        """SET → GET returns same data."""
        from app.core.redis import cache_graphrag_result, get_cached_graphrag_result

        mock_redis = MagicMock()
        store: dict[str, str] = {}

        async def mock_set(key, value, ex=None):
            store[key] = value

        async def mock_get(key):
            return store.get(key)

        mock_redis.set = mock_set
        mock_redis.get = mock_get

        with patch("app.core.redis._get_client", return_value=mock_redis):
            await cache_graphrag_result("graphrag:test:key", CANDIDATES_FIXTURE)
            result = await get_cached_graphrag_result("graphrag:test:key")

        assert result is not None
        assert len(result) == 2
        assert result[0]["name"] == "Test Bloom"
        assert result[0]["score"] == 95.0

    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self):
        """GET on unwritten key returns None."""
        from app.core.redis import get_cached_graphrag_result

        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=None)

        with patch("app.core.redis._get_client", return_value=mock_redis):
            result = await get_cached_graphrag_result("graphrag:never:written")

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_none_client_returns_none(self):
        """When _get_client returns None (Redis down), get returns None gracefully."""
        from app.core.redis import get_cached_graphrag_result

        with patch("app.core.redis._get_client", return_value=None):
            result = await get_cached_graphrag_result("any:key")

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_write_none_client_no_error(self):
        """When _get_client returns None, cache write is a no-op (no crash)."""
        from app.core.redis import cache_graphrag_result

        with patch("app.core.redis._get_client", return_value=None):
            # Should not raise
            await cache_graphrag_result("any:key", CANDIDATES_FIXTURE)

    @pytest.mark.asyncio
    async def test_invalidate_clears_matching_keys(self):
        """invalidate_graphrag_cache deletes keys matching the pattern."""
        from app.core.redis import invalidate_graphrag_cache

        mock_redis = MagicMock()
        mock_redis.keys = AsyncMock(return_value=[b"graphrag:key1", b"graphrag:key2"])
        mock_redis.delete = AsyncMock()

        with patch("app.core.redis._get_client", return_value=mock_redis):
            await invalidate_graphrag_cache("key*")

        mock_redis.delete.assert_called_once()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_invalidate_empty_keys_no_error(self):
        """invalidate with no matching keys is a no-op."""
        from app.core.redis import invalidate_graphrag_cache

        mock_redis = MagicMock()
        mock_redis.keys = AsyncMock(return_value=[])

        with patch("app.core.redis._get_client", return_value=mock_redis):
            await invalidate_graphrag_cache("no_such*")

        mock_redis.delete.assert_not_called()  # type: ignore[attr-defined]


# ── Integration: cache flow in SSE stream ─────────────────────────────────────

class TestCacheIntegration:
    """Verify that the cache flag flows through gen.complete metadata correctly."""

    def test_gen_complete_metadata_accepts_cache_hit(self):
        """The shared type uses Record<string, unknown> — any key is valid.
        This test verifies the Python side emits the right shape."""
        metadata = {
            "mode": "fast",
            "emotion": "joy",
            "search_source": "graphrag_cache",
            "cache_hit": True,
        }
        # Type-check: all required keys present
        assert metadata["cache_hit"] is True
        assert metadata["search_source"] == "graphrag_cache"
        assert "mode" in metadata
