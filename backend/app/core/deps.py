from typing import AsyncGenerator

import asyncpg
from fastapi import Depends, HTTPException, Request, status
from neo4j._async.work.session import AsyncSession

from app.core.pg import get_pg_pool
from app.graph.client import get_neo4j_session


async def get_db_neo4j() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_neo4j_session():
        yield session


async def get_db_pg() -> AsyncGenerator[asyncpg.Connection, None]:
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        yield conn


async def get_current_user(request: Request) -> dict:
    """Extract JWT from Authorization header or ?token= query param, return {id, email}."""
    from app.core.auth import decode_token
    from app.core.pg import get_pg_pool

    token: str | None = None
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        token = auth.removeprefix("Bearer ")
    else:
        # Fallback for EventSource (browser SSE cannot send custom headers)
        token = request.query_params.get("token")

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization header")
    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token type must be 'access'")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing sub claim")

    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email FROM users WHERE id = $1::uuid", user_id
        )
        if not row:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        return {"id": str(row["id"]), "email": row["email"]}
