import asyncio

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


async def _check_neo4j() -> bool:
    try:
        from neo4j import AsyncGraphDatabase
        driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
        async with driver.session() as session:
            await session.run("RETURN 1")
        await driver.close()
        return True
    except Exception:
        return False


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
        await conn.execute("SELECT 1")
        await conn.close()
        return True
    except Exception:
        return False


async def _check_redis() -> bool:
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
        return True
    except Exception:
        return False


@router.get("/health")
async def health():
    neo4j_ok, postgres_ok, redis_ok = await asyncio.gather(
        _check_neo4j(), _check_postgres(), _check_redis(),
    )

    all_ok = neo4j_ok and postgres_ok and redis_ok

    return {
        "status": "ok" if all_ok else "degraded",
        "neo4j": neo4j_ok,
        "postgres": postgres_ok,
        "redis": redis_ok,
    }
