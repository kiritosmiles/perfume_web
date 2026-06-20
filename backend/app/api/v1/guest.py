from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.core.pg import get_pg_pool
from app.models.guest import GuestSessionInput
from app.sse.protocol import sse
from app.sse.stream import sse_event_stream

router = APIRouter()


async def _check_guest_quota(browser_id: str) -> bool:
    """Return True if quota is available (and mark as used), False if exhausted."""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT used FROM guest_quota WHERE browser_id = $1",
            browser_id,
        )
        if row is not None and row["used"]:
            return False  # Already used their free session
        if row is None:
            await conn.execute(
                "INSERT INTO guest_quota (browser_id, used) VALUES ($1, true)",
                browser_id,
            )
        else:
            await conn.execute(
                "UPDATE guest_quota SET used = true WHERE browser_id = $1",
                browser_id,
            )
        return True


async def _quota_exhausted_stream():
    yield sse("gen.error", {
        "generation_id": "",
        "code": "GUEST_QUOTA_EXHAUSTED",
        "user_message": "你已体验过免费推荐，注册账号即可继续使用。",
    })
    yield sse("gen.complete", {
        "generation_id": "",
        "total_cards": 0,
        "metadata": {"reason": "quota_exhausted"},
    })


def _sse_headers() -> dict[str, str]:
    return {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }


@router.post("/guest/sessions")
async def start_guest_session(input_data: GuestSessionInput):
    # Guest quota enforcement (1 free session per browser)
    if input_data.browser_id:
        if not await _check_guest_quota(input_data.browser_id):
            return StreamingResponse(
                _quota_exhausted_stream(),
                media_type="text/event-stream",
                headers=_sse_headers(),
            )

    return StreamingResponse(
        sse_event_stream(input_data),
        media_type="text/event-stream",
        headers=_sse_headers(),
    )


@router.get("/guest/sessions")
async def start_guest_session_get(
    card_ids: str = Query(..., description="Comma-separated emotion card ids, e.g. joy,calm"),
    scene: str = Query(default="", description="Scene tag"),
    browser_id: str = Query(default="", description="Browser identifier"),
):
    card_list = [c.strip() for c in card_ids.split(",") if c.strip()]
    browser_id_val = browser_id or None
    input_data = GuestSessionInput(
        emotion_card_ids=card_list,
        scene_tag=scene or None,
        browser_id=browser_id_val,
    )

    # Guest quota enforcement (same logic as POST)
    if browser_id_val:
        if not await _check_guest_quota(browser_id_val):
            return StreamingResponse(
                _quota_exhausted_stream(),
                media_type="text/event-stream",
                headers=_sse_headers(),
            )

    return StreamingResponse(
        sse_event_stream(input_data),
        media_type="text/event-stream",
        headers=_sse_headers(),
    )
