import asyncio
import logging

from fastapi import APIRouter

from app.core.pg import get_pg_pool
from app.core.redis import check_redis_health
from app.graph.client import check_neo4j_health

logger = logging.getLogger(__name__)
router = APIRouter()


async def _check_postgres() -> bool:
    """Health check using the shared PG pool (no per-request connection)."""
    try:
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.warning("Postgres health check failed: %s", e)
        return False


@router.get("/health")
async def health():
    neo4j_ok, postgres_ok, redis_ok = await asyncio.gather(
        check_neo4j_health(), _check_postgres(), check_redis_health(),
    )

    all_ok = neo4j_ok and postgres_ok and redis_ok

    return {
        "status": "ok" if all_ok else "degraded",
        "neo4j": neo4j_ok,
        "postgres": postgres_ok,
        "redis": redis_ok,
    }
