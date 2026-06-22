"""Memory timeline API — read-only access to L2/L3 summaries."""

import logging

from fastapi import APIRouter, Header, Query, Request, HTTPException

from app.core.pg import get_pg_pool
from app.core.redis import get_l1_fragments

logger = logging.getLogger(__name__)
router = APIRouter()


async def _resolve_owner(request: Request) -> tuple[str, str]:
    """Resolve owner from JWT (auth user) or X-Browser-Id (guest).
    Returns (owner_type, owner_id).
    """
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            from app.core.auth import decode_token
            token = auth.removeprefix("Bearer ")
            payload = decode_token(token)
            if payload.get("type") == "access":
                return ("user", payload["sub"])
        except Exception:
            pass
    browser_id = request.headers.get("X-Browser-Id", "")
    if browser_id:
        return ("guest", browser_id)
    raise HTTPException(status_code=401, detail="Authentication required (Bearer token or X-Browser-Id)")


@router.get("/memory/timeline")
async def get_timeline(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session_id: str = Query(default=""),
):
    """Return memory timeline — L2 + L3 summaries in reverse chronological order."""
    owner_type, owner_id = await _resolve_owner(request)

    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        if owner_type == "user":
            l2_rows = await conn.fetch(
                """SELECT id, text, emotion_profile, round_count, created_at
                   FROM memory_l2 WHERE user_id=$1::uuid
                   ORDER BY created_at DESC LIMIT $2 OFFSET $3""",
                owner_id, limit, offset)
            l3_rows = await conn.fetch(
                """SELECT id, text, preference_keywords, emotion_summary, session_count, created_at
                   FROM memory_l3 WHERE user_id=$1::uuid
                   ORDER BY date DESC LIMIT $2 OFFSET $3""",
                owner_id, limit, offset)
            stats_row = await conn.fetchrow(
                """SELECT
                     (SELECT COUNT(*) FROM memory_l2 WHERE user_id=$1::uuid) AS l2_count,
                     (SELECT COUNT(*) FROM memory_l3 WHERE user_id=$1::uuid) AS l3_count
                """, owner_id)
        else:
            l2_rows = await conn.fetch(
                """SELECT id, text, emotion_profile, round_count, created_at
                   FROM memory_l2 WHERE browser_id=$1
                   ORDER BY created_at DESC LIMIT $2 OFFSET $3""",
                owner_id, limit, offset)
            l3_rows = await conn.fetch(
                """SELECT id, text, preference_keywords, emotion_summary, session_count, created_at
                   FROM memory_l3 WHERE browser_id=$1
                   ORDER BY date DESC LIMIT $2 OFFSET $3""",
                owner_id, limit, offset)
            stats_row = await conn.fetchrow(
                """SELECT
                     (SELECT COUNT(*) FROM memory_l2 WHERE browser_id=$1) AS l2_count,
                     (SELECT COUNT(*) FROM memory_l3 WHERE browser_id=$1) AS l3_count
                """, owner_id)

    l1_count = 0
    if session_id:
        try:
            frags = await get_l1_fragments(session_id, max_rounds=100)
            l1_count = len(frags)
        except Exception:
            pass

    items = []
    for r in l2_rows:
        items.append({
            "level": "L2", "id": str(r["id"]),
            "text": r["text"],
            "emotion_profile": r["emotion_profile"] if isinstance(r.get("emotion_profile"), dict) else {},
            "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
            "metadata": {"round_count": r.get("round_count", 0)},
        })
    for r in l3_rows:
        items.append({
            "level": "L3", "id": str(r["id"]),
            "text": r["text"],
            "emotion_profile": r.get("emotion_summary", {}),
            "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
            "metadata": {
                "preference_keywords": r.get("preference_keywords", []),
                "session_count": r.get("session_count", 0),
            },
        })

    items.sort(key=lambda i: i.get("created_at") or "", reverse=True)

    total = (stats_row["l2_count"] or 0) + (stats_row["l3_count"] or 0) if stats_row else 0

    return {
        "items": items[offset:offset + limit],
        "stats": {
            "l1_count": l1_count,
            "l2_count": stats_row["l2_count"] if stats_row else 0,
            "l3_count": stats_row["l3_count"] if stats_row else 0,
        },
        "total": total,
    }
