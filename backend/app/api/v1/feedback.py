"""Feedback API — explicit (like/dislike) and implicit (dwell, share, refine) events.

Fire-and-forget: always returns 200 to avoid blocking the client.
"""

import json as _json
import logging
import uuid

from fastapi import APIRouter, Request
from app.core.pg import get_pg_pool
from app.models.feedback import ExplicitFeedbackInput, ImplicitFeedbackInput

logger = logging.getLogger(__name__)
router = APIRouter()


def _extract_owner(request: Request) -> tuple[str | None, str | None]:
    """Extract user_id (from auth) or browser_id (from header) from request."""
    browser_id = request.headers.get("X-Browser-Id") or None
    # Auth user extraction happens via dependency, but we support both.
    # For now, browser_id covers guest + authenticated with header.
    return None, browser_id


@router.post("/feedback/explicit", status_code=202)
async def submit_explicit_feedback(
    body: ExplicitFeedbackInput,
    request: Request,
):
    """Record explicit feedback (like/dislike) on a recommendation card."""
    _, browser_id = _extract_owner(request)

    feedback_id = str(uuid.uuid4())
    try:
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO feedback (id, browser_id, generation_id, feedback_type, event_name, payload)
                VALUES ($1, $2, $3, 'explicit', $4, $5)
                """,
                feedback_id,
                browser_id,
                body.generation_id,
                f"{body.reaction}_card",
                _json.dumps({"card_rank": body.card_rank, "reason": body.reason} if body.reason else {
                    "card_rank": body.card_rank,
                }, ensure_ascii=False),
            )
    except Exception:
        logger.warning("Failed to record explicit feedback gen=%s rank=%d",
                       body.generation_id, body.card_rank, exc_info=True)

    return {"status": "recorded", "feedback_id": feedback_id}


@router.post("/feedback/implicit", status_code=202)
async def submit_implicit_feedback(
    body: ImplicitFeedbackInput,
    request: Request,
):
    """Record batch of implicit events (dwell, share, refine, etc.)."""
    _, browser_id = _extract_owner(request)

    recorded = 0
    try:
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            for event in body.events:
                evt_id = str(uuid.uuid4())
                await conn.execute(
                    """
                    INSERT INTO feedback (id, browser_id, generation_id, feedback_type, event_name, payload)
                    VALUES ($1, $2, $3, 'implicit', $4, $5)
                    """,
                    evt_id,
                    browser_id,
                    body.generation_id,
                    event.event_name,
                    _json.dumps(event.payload, ensure_ascii=False),
                )
                recorded += 1
    except Exception:
        logger.warning("Failed to record implicit feedback gen=%s count=%d",
                       body.generation_id, len(body.events), exc_info=True)

    return {"status": "recorded", "events_recorded": recorded}
