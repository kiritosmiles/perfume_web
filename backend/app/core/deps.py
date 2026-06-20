from typing import AsyncGenerator

import asyncpg
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
