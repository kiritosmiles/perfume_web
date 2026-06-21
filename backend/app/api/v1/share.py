"""Share link endpoints — create and read shared recommendation cards."""

import json
import logging
import secrets
import string
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.pg import get_pg_pool

logger = logging.getLogger(__name__)
router = APIRouter()

ALPHABET = string.ascii_lowercase + string.digits
ID_LENGTH = 8


def _generate_share_id() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(ID_LENGTH))


class ShareInput(BaseModel):
    recommendations: list[dict] = Field(..., min_length=1, max_length=3)
    emotion: dict = Field(...)
    scene_tag: str | None = None
    generation_id: str | None = None


class ShareResponse(BaseModel):
    share_id: str
    share_url: str


@router.post("/share")
async def create_share(input_data: ShareInput) -> ShareResponse:
    payload = {
        "recommendations": input_data.recommendations,
        "emotion": input_data.emotion,
        "scene_tag": input_data.scene_tag,
        "generation_id": input_data.generation_id,
    }
    share_id = _generate_share_id()
    try:
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO share_links (id, payload, created_at, expires_at)
                VALUES ($1, $2, now(), now() + INTERVAL '7 days')
                """,
                share_id,
                json.dumps(payload, ensure_ascii=False),
            )
    except Exception as e:
        logger.error("Failed to create share link: %s", e)
        raise HTTPException(status_code=500, detail="Failed to create share link")
    logger.info("Share link created: %s", share_id)
    return ShareResponse(share_id=share_id, share_url=f"/s/{share_id}")


@router.get("/share/{share_id}")
async def get_share(share_id: str):
    if len(share_id) != ID_LENGTH or not all(c in ALPHABET for c in share_id):
        raise HTTPException(status_code=404, detail="Share link not found")
    try:
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT payload, created_at, expires_at FROM share_links WHERE id = $1",
                share_id,
            )
    except Exception as e:
        logger.error("Failed to fetch share link %s: %s", share_id, e)
        raise HTTPException(status_code=500, detail="Failed to retrieve share link")
    if row is None:
        raise HTTPException(status_code=404, detail="Share link not found")
    expires_at = row["expires_at"]
    if expires_at and expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="This share link has expired")
    return {
        "share_id": share_id,
        "payload": json.loads(row["payload"]),
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "expires_at": expires_at.isoformat() if expires_at else None,
    }
