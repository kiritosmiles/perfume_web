import asyncio
import logging

from fastapi import APIRouter

from app.core.config import settings
from app.graph.client import check_neo4j_health

logger = logging.getLogger(__name__)
router = APIRouter()


async def _check_postgres() -> bool:
    try:
        import asyncpg
        conn = await asyncpg.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME,
        )
        try:
            await conn.execute("SELECT 1")
        finally:
            await conn.close()
        return True
    except Exception as e:
        logger.warning("Postgres health check failed: %s", e)
        return False


async def _check_redis() -> bool:
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL)
        try:
            await r.ping()
        finally:
            await r.aclose()
        return True
    except Exception as e:
        logger.warning("Redis health check failed: %s", e)
        return False


@router.get("/health")
async def health():
    neo4j_ok, postgres_ok, redis_ok = await asyncio.gather(
        check_neo4j_health(), _check_postgres(), _check_redis(),
    )

    all_ok = neo4j_ok and postgres_ok and redis_ok

    return {
        "status": "ok" if all_ok else "degraded",
        "neo4j": neo4j_ok,
        "postgres": postgres_ok,
        "redis": redis_ok,
    }
