"""Redis async client — shared connection for caching and rate limiting.

Uses redis.asyncio for non-blocking Redis operations from FastAPI async handlers.
"""

from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

_client: aioredis.Redis | None = None


async def init_redis() -> None:
    global _client
    _client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    await _client.ping()


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def _get_client() -> aioredis.Redis | None:
    """Return the Redis client, or None if not initialized.

    All callers must handle None gracefully — Redis is an optional caching layer.
    """
    return _client


# ── Emotion vector cache ─────────────────────────────────────────────────────

EMOTION_CACHE_TTL = 3600  # 1 hour


async def cache_emotion_vector(card_key: str, vector: dict[str, float]) -> None:
    """Cache resolved emotion vector by sorted card-id key.

    Gracefully does nothing if Redis is not initialized.
    """
    r = _get_client()
    if r is None:
        return
    await r.hset(
        f"emotion:{card_key}",
        mapping={k: str(v) for k, v in vector.items()},
    )
    await r.expire(f"emotion:{card_key}", EMOTION_CACHE_TTL)


async def get_cached_emotion_vector(card_key: str) -> dict[str, float] | None:
    """Retrieve cached emotion vector. Returns None on cache miss or Redis unavailable."""
    r = _get_client()
    if r is None:
        return None
    raw = await r.hgetall(f"emotion:{card_key}")
    if not raw:
        return None
    return {k: float(v) for k, v in raw.items()}


# ── Guest quota rate-limit (Redis-layer, complements PG table) ────────────────

QUOTA_WINDOW = 86400 * 30  # 30 days


async def check_redis_quota(browser_id: str) -> bool:
    """Return True if quota available, False if exhausted.

    When Redis is unavailable, defaults to True (allow) — PG is the durable layer.
    """
    r = _get_client()
    if r is None:
        return True  # Degrade: allow, PG will enforce
    key = f"guest_quota:{browser_id}"
    exists = await r.exists(key)
    if exists:
        return False  # Already used
    await r.set(key, "1", ex=QUOTA_WINDOW)
    return True


async def reset_redis_quota(browser_id: str) -> None:
    """Remove quota key (admin/testing). No-op if Redis unavailable."""
    r = _get_client()
    if r is None:
        return
    await r.delete(f"guest_quota:{browser_id}")


# ── User-provided LLM key (24h TTL per browser session) ────────────────────────

LLM_KEY_TTL = 86400  # 24 hours


async def store_llm_key(browser_id: str, api_key: str, base_url: str | None = None) -> None:
    """Store user-provided LLM API key in Redis, keyed by browser_id.

    Gracefully does nothing if Redis is not initialized.
    """
    r = _get_client()
    if r is None:
        return
    import json
    data = json.dumps({"api_key": api_key, "base_url": base_url or ""})
    await r.set(f"llm_key:{browser_id}", data, ex=LLM_KEY_TTL)


async def get_llm_key(browser_id: str) -> dict | None:
    """Retrieve user-provided LLM key. Returns None if not set or Redis unavailable."""
    r = _get_client()
    if r is None:
        return None
    import json
    raw = await r.get(f"llm_key:{browser_id}")
    if not raw:
        return None
    return json.loads(raw)


# ── Health check ──────────────────────────────────────────────────────────────

async def check_redis_health() -> bool:
    try:
        r = _get_client()
        if r is None:
            return False
        await r.ping()
        return True
    except Exception:
        return False
