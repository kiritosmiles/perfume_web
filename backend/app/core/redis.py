"""Redis async client — shared connection for caching and rate limiting.

Uses redis.asyncio for non-blocking Redis operations from FastAPI async handlers.
"""

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)
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


# ── L1 Memory fragment layer ────────────────────────────────────────────────────

L1_MEMORY_TTL = 86400  # 24h


async def write_l1_evidence(
    session_id: str, round_num: int,
    user_text: str, agent_text: str,
    emotion_vector: dict[str, float],
) -> None:
    r = _get_client()
    if r is None:
        return
    import json as _json, datetime as _dt
    await r.hset(f"memory:L1:{session_id}:{round_num}", mapping={
        "user_text": user_text[:2000],
        "agent_text": agent_text[:2000],
        "text": "",
        "round_num": str(round_num),
        "emotion_vector": _json.dumps(emotion_vector, ensure_ascii=False),
        "timestamp": _dt.datetime.now().isoformat(),
    })
    await r.expire(f"memory:L1:{session_id}:{round_num}", L1_MEMORY_TTL)


async def get_l1_fragments(session_id: str, max_rounds: int = 20) -> list[dict]:
    r = _get_client()
    if r is None:
        return []
    import json as _json
    frags = []
    for rn in range(1, max_rounds + 1):
        data = await r.hgetall(f"memory:L1:{session_id}:{rn}")
        if not data:
            continue
        try:
            frags.append({
                "user_text": data.get("user_text", ""),
                "agent_text": data.get("agent_text", ""),
                "text": data.get("text", ""),
                "round_num": int(data.get("round_num", 0)),
                "emotion_vector": _json.loads(data.get("emotion_vector", "{}")),
                "timestamp": data.get("timestamp", ""),
            })
        except Exception:
            logger.debug("L1 fragment parse error session=%s round=%d", session_id, rn, exc_info=True)
    frags.sort(key=lambda f: f["round_num"])
    return frags


async def update_l1_text(session_id: str, round_num: int, text: str) -> None:
    r = _get_client()
    if r is None:
        return
    await r.hset(f"memory:L1:{session_id}:{round_num}", "text", text[:2000])
    await r.expire(f"memory:L1:{session_id}:{round_num}", L1_MEMORY_TTL)


async def get_l1_texts(session_id: str) -> list[str]:
    frags = await get_l1_fragments(session_id)
    return [f["text"] for f in frags if f.get("text")]


# ── GraphRAG result cache (hot-path, card-preset only) ─────────────────────────

GRAPHRAG_CACHE_TTL = 3600  # 1 hour


def build_graphrag_cache_key(emotion_vector: dict[str, float], scene_tag: str | None) -> str:
    """Build a deterministic cache key from emotion vector + scene tag.

    Dimensions are sorted alphabetically for consistency regardless of dict
    insertion order. Tiny values (≤0.05) are dropped to prevent key explosion
    from float noise after normalization.
    """
    sorted_dims = sorted(emotion_vector.items())
    vec_part = "+".join(
        f"{k}:{v:.3f}" for k, v in sorted_dims if v > 0.05
    )
    scene = scene_tag or "none"
    return f"graphrag:{vec_part}:{scene}"


async def cache_graphrag_result(key: str, candidates: list[dict], ttl: int = GRAPHRAG_CACHE_TTL) -> None:
    """Cache GraphRAG search results keyed by build_graphrag_cache_key output.

    Gracefully does nothing if Redis is not initialized.
    """
    r = _get_client()
    if r is None:
        return
    try:
        await r.set(key, json.dumps(candidates, ensure_ascii=False), ex=ttl)
    except Exception:
        logger.debug("GraphRAG cache write failed key=%s", key, exc_info=True)


async def get_cached_graphrag_result(key: str) -> list[dict] | None:
    """Retrieve cached GraphRAG candidates. Returns None on miss or Redis unavailable."""
    r = _get_client()
    if r is None:
        return None
    try:
        raw = await r.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception:
        logger.debug("GraphRAG cache read failed key=%s", key, exc_info=True)
        return None


async def invalidate_graphrag_cache(pattern: str = "*") -> None:
    """Delete cached GraphRAG results matching a glob pattern.

    pattern="*" (default) clears all GraphRAG cache entries.
    pattern="joy*" clears entries with primary emotion = joy.
    No-op if Redis is unavailable.
    """
    r = _get_client()
    if r is None:
        return
    try:
        full_pattern = f"graphrag:{pattern}"
        keys = await r.keys(full_pattern)
        if keys:
            await r.delete(*keys)
    except Exception:
        logger.debug("GraphRAG cache invalidation failed pattern=%s", pattern, exc_info=True)


# ── Boundary overstep counter (FR-5.9) ─────────────────────────────────────────

BOUNDARY_OVERSTEP_TTL = 86400  # 24h — matches session lifetime


async def increment_boundary_overstep(session_id: str) -> int:
    """Increment and return the boundary overstep counter for a session.

    Used by FR-5.9: 3 consecutive overstep → forced human handoff.

    Returns the new count or -1 if Redis is unavailable (caller treats as counter=0).
    """
    r = _get_client()
    if r is None:
        return -1
    key = f"boundary:overstep:{session_id}"
    try:
        count = await r.incr(key)
        await r.expire(key, BOUNDARY_OVERSTEP_TTL)
        return count
    except Exception:
        logger.debug("Boundary counter increment failed session=%s", session_id, exc_info=True)
        return -1


async def reset_boundary_overstep(session_id: str) -> None:
    """Reset overstep counter for a session (e.g. after handoff or new session).

    No-op if Redis is unavailable.
    """
    r = _get_client()
    if r is None:
        return
    try:
        await r.delete(f"boundary:overstep:{session_id}")
    except Exception:
        pass


# ── Skeleton cache (FR: Phase 4 — copy text degradation fallback) ─────────────

SKELETON_CACHE_TTL = 86400  # 24 hours


def build_skeleton_cache_key(
    emotion_vector: dict[str, float],
    intent: str,
    scene_tag: str | None,
) -> str:
    """Build a deterministic cache key from emotion vector + intent + scene.

    Same pattern as build_graphrag_cache_key: sorted dims alphabetically,
    .3f precision, tiny values (<=0.05) dropped.

    Example key: skeleton:anxiety:0.350+calm:0.120+joy:0.160:self_use:none
    """
    sorted_dims = sorted(emotion_vector.items())
    vec_part = "+".join(
        f"{k}:{v:.3f}" for k, v in sorted_dims if v > 0.05
    )
    scene = scene_tag or "none"
    return f"skeleton:{vec_part}:{intent}:{scene}"


async def cache_skeleton(
    key: str,
    skeleton_data: list[dict],
    ttl: int = SKELETON_CACHE_TTL,
) -> None:
    """Cache skeleton cards (with copy_full_text) for LLM degradation fallback.

    Stores the full skeleton array as JSON. Each skeleton dict should include
    the LLM-generated copy_full_text field for later cache-hit streaming.

    Fire-and-forget — caller should not await this in the hot path.
    Gracefully does nothing if Redis is not initialized.
    """
    r = _get_client()
    if r is None:
        return
    try:
        await r.set(key, json.dumps(skeleton_data, ensure_ascii=False), ex=ttl)
    except Exception:
        logger.debug("Skeleton cache write failed key=%s", key, exc_info=True)


async def get_cached_skeleton(key: str) -> list[dict] | None:
    """Retrieve cached skeleton cards. Returns None on miss or Redis unavailable."""
    r = _get_client()
    if r is None:
        return None
    try:
        raw = await r.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception:
        logger.debug("Skeleton cache read failed key=%s", key, exc_info=True)
        return None


# ── Generation concurrency lock (Phase 4: multi-tab concurrency) ──────────────

CONCURRENCY_LOCK_TTL = 30  # seconds — auto-release if generation crashes


async def acquire_generation_lock(owner_key: str, lock_id: str) -> bool:
    """Try to acquire a per-user generation lock. Uses Redis SET NX for atomicity.

    owner_key = user_id (auth) or browser_id (guest) or session_id (fallback).
    Returns True if lock acquired, False if another tab/request holds it.

    Redis down → allow (optimistic — don't block user).
    """
    r = _get_client()
    if r is None:
        return True  # Redis down → optimistic
    try:
        key = f"gen_lock:{owner_key}"
        acquired = await r.set(key, lock_id, nx=True, ex=CONCURRENCY_LOCK_TTL)
        return bool(acquired)
    except Exception:
        return True  # Error → optimistic


async def release_generation_lock(owner_key: str, lock_id: str) -> None:
    """Release a per-user generation lock. Only deletes if we still hold it."""
    r = _get_client()
    if r is None:
        return
    try:
        key = f"gen_lock:{owner_key}"
        current = await r.get(key)
        if current == lock_id:
            await r.delete(key)
    except Exception:
        pass


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
