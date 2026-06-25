"""Auth endpoints: register, login, refresh, me."""

import hashlib
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.auth import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, decode_token,
)
from app.core.deps import get_current_user
from app.core.pg import get_pg_pool
from app.core.ratelimit import check_rate_limit
from app.models.auth import RegisterInput, LoginInput, RefreshInput

logger = logging.getLogger(__name__)
router = APIRouter()


def _user_response(row) -> dict:
    return {
        "id": str(row["id"]),
        "email": row["email"],
        "feature_tier": row.get("feature_tier", "free"),
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
    }


@router.post("/auth/register")
async def register(input_data: RegisterInput, request: Request):
    await check_rate_limit(request)
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT id FROM users WHERE email = $1", input_data.email)
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")

        pw_hash = hash_password(input_data.password)
        row = await conn.fetchrow(
            "INSERT INTO users (email, password_hash) VALUES ($1, $2) RETURNING id, email, created_at",
            input_data.email, pw_hash,
        )
        user_id = str(row["id"])

        # Migrate guest data if browser_id provided
        if input_data.browser_id:
            try:
                await conn.execute(
                    "UPDATE temp_conversations SET user_id = $1::uuid WHERE browser_id = $2 AND user_id IS NULL",
                    user_id, input_data.browser_id,
                )
            except Exception:
                logger.warning("Guest data migration failed for browser_id=%s", input_data.browser_id)

            # Migrate memory data from browser_id to user_id
            if input_data.browser_id:
                try:
                    await conn.execute(
                        "UPDATE memory_l2 SET user_id=$1::uuid, browser_id=NULL WHERE browser_id=$2 AND user_id IS NULL",
                        user_id, input_data.browser_id)
                    await conn.execute(
                        "UPDATE memory_l3 SET user_id=$1::uuid, browser_id=NULL WHERE browser_id=$2 AND user_id IS NULL",
                        user_id, input_data.browser_id)
                except Exception:
                    logger.warning("Memory migration failed for browser_id=%s", input_data.browser_id)

        access = create_access_token(user_id, feature_tier=row.get("feature_tier", "free"))
        refresh_raw, refresh_hash = create_refresh_token(user_id)
        expires = datetime.now(timezone.utc) + timedelta(days=7)
        await conn.execute(
            "INSERT INTO refresh_tokens (user_id, token_hash, expires_at) VALUES ($1::uuid, $2, $3)",
            user_id, refresh_hash, expires,
        )

        return {
            "user": _user_response(row),
            "access_token": access,
            "refresh_token": refresh_raw,
        }


@router.post("/auth/login")
async def login(input_data: LoginInput, request: Request):
    await check_rate_limit(request)
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, password_hash, created_at, feature_tier FROM users WHERE email = $1",
            input_data.email,
        )
        if not row:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if not verify_password(input_data.password, row["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        user_id = str(row["id"])
        access = create_access_token(user_id, feature_tier=row.get("feature_tier", "free"))
        refresh_raw, refresh_hash = create_refresh_token(user_id)
        expires = datetime.now(timezone.utc) + timedelta(days=7)
        await conn.execute(
            "INSERT INTO refresh_tokens (user_id, token_hash, expires_at) VALUES ($1::uuid, $2, $3)",
            user_id, refresh_hash, expires,
        )

        return {
            "user": _user_response(row),
            "access_token": access,
            "refresh_token": refresh_raw,
        }


@router.post("/auth/refresh")
async def refresh(input_data: RefreshInput):
    try:
        payload = decode_token(input_data.refresh_token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Token must be type 'refresh'")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing sub")

    token_hash = hashlib.sha256(input_data.refresh_token.encode()).hexdigest()

    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM refresh_tokens WHERE token_hash = $1 AND expires_at > now()",
            token_hash,
        )
        if not row:
            raise HTTPException(status_code=401, detail="Refresh token not found or expired")

        await conn.execute("DELETE FROM refresh_tokens WHERE token_hash = $1", token_hash)

        user = await conn.fetchrow(
            "SELECT id, email, created_at, feature_tier FROM users WHERE id = $1::uuid", user_id,
        )
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        access = create_access_token(user_id, feature_tier=user.get("feature_tier", "free"))
        refresh_raw, new_hash = create_refresh_token(user_id)
        expires = datetime.now(timezone.utc) + timedelta(days=7)
        await conn.execute(
            "INSERT INTO refresh_tokens (user_id, token_hash, expires_at) VALUES ($1::uuid, $2, $3)",
            user_id, new_hash, expires,
        )

        return {
            "user": _user_response(user),
            "access_token": access,
            "refresh_token": refresh_raw,
        }


@router.get("/auth/me")
async def me(current_user: dict = Depends(get_current_user)):
    return current_user
