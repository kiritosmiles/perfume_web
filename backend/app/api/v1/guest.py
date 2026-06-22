import logging

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.core.pg import get_pg_pool
from app.core.ratelimit import rate_limit_guest
from app.core.redis import check_redis_quota
from app.models.guest import GuestSessionInput
from app.sse.protocol import sse
from app.sse.stream import sse_event_stream

logger = logging.getLogger(__name__)
router = APIRouter()


async def _check_guest_quota(browser_id: str) -> bool:
    """Two-layer quota: Redis (fast, 30d TTL) + PG (durable).

    Returns True if quota is available (and marks as used), False if exhausted.
    """
    if not await check_redis_quota(browser_id):
        return False
    try:
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT used FROM guest_quota WHERE browser_id = $1",
                browser_id,
            )
            if row is not None and row["used"]:
                return False
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
    except Exception:
        logger.warning("PG quota check failed for %s, trusting Redis", browser_id)
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
async def start_guest_session(input_data: GuestSessionInput, request: Request):
    # Rate limit (TRD §6.2: 30 POST/min)
    if not await rate_limit_guest(request):
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "RATE_LIMITED",
                    "message": "请求过于频繁，请稍后再试。",
                    "retryable": True,
                    "details": {"retry_after_seconds": 60},
                }
            },
            headers={"Retry-After": "60"},
        )

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
    request: Request,
    card_ids: str = Query(default="", description="Comma-separated emotion card ids, e.g. joy,calm"),
    scene: str = Query(default="", description="Scene tag"),
    browser_id: str = Query(default="", description="Browser identifier"),
    text: str = Query(default="", description="Free-text mood description (alternative to card_ids)"),
):
    # Rate limit (TRD §6.2: 120 GET/min)
    if not await rate_limit_guest(request):
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "RATE_LIMITED",
                    "message": "请求过于频繁，请稍后再试。",
                    "retryable": True,
                    "details": {"retry_after_seconds": 60},
                }
            },
            headers={"Retry-After": "60"},
        )

    card_list = [c.strip() for c in card_ids.split(",") if c.strip()]
    browser_id_val = browser_id or None
    text_val = text.strip() or None
    input_data = GuestSessionInput(
        emotion_card_ids=card_list,
        scene_tag=scene or None,
        browser_id=browser_id_val,
        user_text=text_val,
    )

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
