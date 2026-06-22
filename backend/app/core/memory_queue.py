"""Redis Queue for L2/L3 async consolidation — RPUSH/BRPOP."""

import json as _json
import logging

from app.core.redis import _get_client

logger = logging.getLogger(__name__)
MAX_RETRIES = 3

L2_QUEUE_KEY = "memory:queue:L2"
L2_DEAD_KEY = "memory:queue:L2:dead"
L3_QUEUE_KEY = "memory:queue:L3"
L3_DEAD_KEY = "memory:queue:L3:dead"


async def enqueue_l2(owner_type: str, owner_id: str, session_id: str) -> None:
    r = _get_client()
    if r is None:
        logger.warning("Redis unavailable, L2 enqueue skipped: %s", session_id)
        return
    payload = _json.dumps({"owner_type": owner_type, "owner_id": owner_id, "session_id": session_id})
    await r.rpush(L2_QUEUE_KEY, payload)
    logger.debug("L2 enqueued: session=%s", session_id)


async def dequeue_l2(timeout_seconds: int = 30) -> dict | None:
    r = _get_client()
    if r is None:
        return None
    result = await r.brpop(L2_QUEUE_KEY, timeout_seconds)
    if result is None:
        return None
    return _json.loads(result[1])


async def dead_letter_l2(task: dict) -> None:
    r = _get_client()
    if r is None:
        return
    await r.rpush(L2_DEAD_KEY, _json.dumps(task))
    logger.warning("L2 task dead-lettered: %s", task.get("session_id"))


async def enqueue_l3(owner_type: str, owner_id: str, date_str: str) -> None:
    r = _get_client()
    if r is None:
        return
    await r.rpush(L3_QUEUE_KEY, _json.dumps({"owner_type": owner_type, "owner_id": owner_id, "date": date_str}))


async def dead_letter_l3(task: dict) -> None:
    r = _get_client()
    if r is None:
        return
    await r.rpush(L3_DEAD_KEY, _json.dumps(task))
