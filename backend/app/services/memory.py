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
