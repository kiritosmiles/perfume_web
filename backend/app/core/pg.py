"""PostgreSQL async pool singleton for backend services.

Mirrors the pattern in app/graph/client.py — module-level pool with
initialization from FastAPI lifespan. Not a connection-per-request pool;
services acquire/release connections from this shared pool.
"""

import asyncpg

from app.core.config import settings

_pool: asyncpg.Pool | None = None


async def init_pg_pool() -> None:
    global _pool
    _pool = await asyncpg.create_pool(
        dsn=settings.pg_dsn,
        min_size=2,
        max_size=10,
    )


async def close_pg_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def get_pg_pool() -> asyncpg.Pool:
    """Return the shared pool, lazily initializing on first call if needed."""
    global _pool
    if _pool is None:
        await init_pg_pool()
    assert _pool is not None, "PG pool initialization failed"
    return _pool
