from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from app.models.guest import GuestSessionInput
from app.services.safety import crisis_check
from app.sse.stream import sse_event_stream

router = APIRouter()


@router.post("/guest/sessions")
async def start_guest_session(input_data: GuestSessionInput):
    # Safety check before streaming
    # Combine card labels for safety check (simplified - no text input in MVP)
    check = crisis_check("")
    if check["is_crisis"] and check["severity"] == "high":
        from app.sse.protocol import sse
        return StreamingResponse(
            _safety_block_stream(check),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return StreamingResponse(
        sse_event_stream(input_data),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/guest/sessions")
async def start_guest_session_get(
    card_ids: str = Query(..., description="Comma-separated emotion card ids, e.g. joy,calm"),
    scene: str = Query(default="", description="Scene tag"),
    browser_id: str = Query(default="", description="Browser identifier"),
):
    card_list = [c.strip() for c in card_ids.split(",") if c.strip()]
    input_data = GuestSessionInput(
        emotion_card_ids=card_list,
        scene_tag=scene or None,
        browser_id=browser_id or None,
    )

    return StreamingResponse(
        sse_event_stream(input_data),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _safety_block_stream(check: dict):
    from app.sse.protocol import sse as sse_fmt
    yield sse_fmt("safety.block", {
        "reason": "crisis_content",
        "user_message": "我们检测到你可能需要专业帮助。建议联系心理援助热线。",
    })
