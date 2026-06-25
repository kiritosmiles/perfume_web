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
    allergens: str = Query(default=""),
    refine: str = Query(default=""),
    gate_answer: str = Query(default=""),
    intent: str = Query(default="self_use"),
    season: str = Query(default=""),
    time_of_day: str = Query(default=""),
    weather_code: str = Query(default=""),
    temperature: str = Query(default=""),
    diversity: str = Query(default="0.0"),
    session_mode: str = Query(default="context"),
    recipient_age_range: str = Query(default=""),
    recipient_relationship: str = Query(default=""),
    recipient_gender_pref: str = Query(default=""),
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
    allergens_list = [a.strip() for a in allergens.split(",") if a.strip()]
    refine_val = refine.strip() or None
    gate_answer_val = gate_answer.strip() or None
    intent_val = intent.strip() if intent.strip() in ("self_use", "gift", "explore") else "self_use"
    season_val = season.strip() or None
    time_of_day_val = time_of_day.strip() or None
    weather_code_val = int(weather_code) if weather_code.strip() else None
    temp_val = float(temperature) if temperature.strip() else None
    diversity_val = float(diversity) if diversity.strip() else 0.0
    session_mode_val = session_mode.strip() or "context"
    ra_val = recipient_age_range.strip() or None
    rr_val = recipient_relationship.strip() or None
    rg_val = recipient_gender_pref.strip() or None
    input_data = GuestSessionInput(
        emotion_card_ids=card_list,
        scene_tag=scene or None,
        browser_id=None,
        user_text=text_val,
        allergens=allergens_list or None,
        refine=refine_val,
        gate_answer=gate_answer_val,
        intent=intent_val,  # type: ignore[arg-type]
        season=season_val,
        time_of_day=time_of_day_val,
        weather_code=weather_code_val,
        temperature=temp_val,
        diversity=diversity_val,
        session_mode=session_mode_val,  # type: ignore[arg-type]
        recipient_age_range=ra_val,
        recipient_relationship=rr_val,
        recipient_gender_pref=rg_val,
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
