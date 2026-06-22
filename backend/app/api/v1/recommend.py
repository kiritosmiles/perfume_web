"""Authenticated recommend SSE endpoint with quota enforcement."""

import logging

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from app.core.deps import get_current_user
from app.core.quota import check_free_quota, consume_free_quota, get_remaining_quota
from app.core.ratelimit import check_rate_limit
from app.models.guest import GuestSessionInput
from app.sse.protocol import sse
from app.sse.stream import sse_event_stream

logger = logging.getLogger(__name__)
router = APIRouter()


async def _quota_exhausted_stream(quota_type: str = "sessions"):
    yield sse("gen.error", {
        "generation_id": "",
        "code": "QUOTA_EXHAUSTED",
        "user_message": f"Daily {quota_type} limit reached. Resets at midnight UTC.",
    })
    yield sse("gen.complete", {
        "generation_id": "",
        "total_cards": 0,
        "metadata": {"reason": "quota_exhausted", "quota_type": quota_type},
    })


def _sse_headers() -> dict[str, str]:
    return {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }


@router.post("/recommend/sessions")
async def start_auth_session(
    input_data: GuestSessionInput,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    await check_rate_limit(request)
    user_id = current_user["id"]
    if not await check_free_quota(user_id, "sessions"):
        return StreamingResponse(
            _quota_exhausted_stream("sessions"),
            media_type="text/event-stream",
            headers=_sse_headers(),
        )
    await consume_free_quota(user_id, "sessions")
    return StreamingResponse(
        sse_event_stream(input_data, user_id=user_id),
        media_type="text/event-stream",
        headers=_sse_headers(),
    )


@router.get("/recommend/sessions")
async def start_auth_session_get(
    request: Request,
    card_ids: str = Query(default=""),
    scene: str = Query(default=""),
    text: str = Query(default=""),
    current_user: dict = Depends(get_current_user),
):
    await check_rate_limit(request)
    user_id = current_user["id"]
    if not await check_free_quota(user_id, "sessions"):
        return StreamingResponse(
            _quota_exhausted_stream("sessions"),
            media_type="text/event-stream",
            headers=_sse_headers(),
        )
    await consume_free_quota(user_id, "sessions")
    card_list = [c.strip() for c in card_ids.split(",") if c.strip()]
    text_val = text.strip() or None
    input_data = GuestSessionInput(
        emotion_card_ids=card_list,
        scene_tag=scene or None,
        browser_id=None,
        user_text=text_val,
    )
    return StreamingResponse(
        sse_event_stream(input_data, user_id=user_id),
        media_type="text/event-stream",
        headers=_sse_headers(),
    )


@router.get("/recommend/quota")
async def get_quota(current_user: dict = Depends(get_current_user)):
    """Return current user's quota usage for all types."""
    return await get_remaining_quota(current_user["id"])
