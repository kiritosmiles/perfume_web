"""Rate limiting using Redis sliding-window counters.

TRD §6.2 limits: POST 30 req/min, GET 120 req/min per client.
Keyed by client IP (always available, no body-read race).
"""

import time
import logging

from starlette.requests import Request

from app.core.redis import _get_client

logger = logging.getLogger(__name__)

WL_POST = 30       # requests per window
WL_GET  = 120
WINDOW  = 60       # seconds


async def check_rate_limit(request: Request) -> None:
    """Raise no exception — just check. Callers decide what to do.

    Returns (allowed: bool, retry_after: int).
    """
    r = _get_client()
    if r is None:
        return  # Redis unavailable → allow

    ip = request.client.host if request.client else "127.0.0.1"
    limit = WL_POST if request.method == "POST" else WL_GET
    now = int(time.time())
    window_key = f"rate:{ip}:{now // WINDOW}"

    count = await r.incr(window_key)
    if count == 1:
        await r.expire(window_key, WINDOW + 5)
    if count > limit:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait a minute.",
        )


async def rate_limit_guest(request: Request) -> bool:
    """Return True if within limit. False = exceeded, caller should 429."""
    r = _get_client()
    if r is None:
        return True  # Redis unavailable → allow

    ip = request.client.host if request.client else "127.0.0.1"
    limit = WL_POST if request.method == "POST" else WL_GET
    now = int(time.time())
    window_key = f"rate:{ip}:{now // WINDOW}"

    count = await r.incr(window_key)
    if count == 1:
        await r.expire(window_key, WINDOW + 5)
    return count <= limit
