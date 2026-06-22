"""Unified memory API — write/read/consolidate across L1/L2/L3."""

import logging

from app.core.redis import write_l1_evidence, get_l1_fragments, update_l1_text, get_l1_texts

logger = logging.getLogger(__name__)


async def trigger_l1_consolidation(
    session_id: str, round_num: int,
    user_text: str, agent_text: str,
    history_facts: list[str],
) -> None:
    """Fire-and-forget L1 consolidation: LLM summary → update Redis text field.
    Runs ~500ms async — never blocks the SSE stream.
    """
    try:
        from app.core.consolidator import consolidate_l1
        summary = await consolidate_l1(user_text, agent_text, history_facts)
        if summary:
            await update_l1_text(session_id, round_num, summary)
            logger.debug("L1 consolidated: session=%s round=%d", session_id, round_num)
    except Exception:
        logger.warning("L1 consolidation failed session=%s round=%d", session_id, round_num, exc_info=True)


from app.core.pg import get_pg_pool
from app.core.memory_queue import enqueue_l2 as _enq_l2
from app.core.consolidator import consolidate_l2
from app.core.embedding import encode


async def get_l2_summaries(owner_type: str, owner_id: str, limit: int = 3) -> list[str]:
    try:
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            if owner_type == "user":
                rows = await conn.fetch(
                    "SELECT text FROM memory_l2 WHERE user_id=$1::uuid ORDER BY created_at DESC LIMIT $2",
                    owner_id, limit)
            else:
                rows = await conn.fetch(
                    "SELECT text FROM memory_l2 WHERE browser_id=$1 ORDER BY created_at DESC LIMIT $2",
                    owner_id, limit)
            return [r["text"] for r in rows]
    except Exception:
        logger.warning("get_l2_summaries failed", exc_info=True)
        return []


async def consolidate_session_to_l2(owner_type: str, owner_id: str, session_id: str) -> bool:
    try:
        l1_texts = await get_l1_texts(session_id)
        if not l1_texts:
            logger.info("L2 skip: no L1 texts for session=%s", session_id)
            return True
        recent = await get_l2_summaries(owner_type, owner_id, 3)
        summary = await consolidate_l2(l1_texts, recent)
        if not summary:
            return False
        emb = await encode(summary)
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            uid = owner_id if owner_type == "user" else None
            bid = owner_id if owner_type == "guest" else None
            await conn.execute(
                """INSERT INTO memory_l2 (user_id, browser_id, session_id, text, embedding, round_count)
                   VALUES ($1::uuid, $2, $3::uuid, $4, $5, $6)
                   ON CONFLICT DO NOTHING""",
                uid, bid, session_id, summary, emb, len(l1_texts))
        logger.info("L2 done: session=%s", session_id)
        return True
    except Exception:
        logger.warning("L2 consolidation failed session=%s", session_id, exc_info=True)
        return False
