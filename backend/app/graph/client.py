import threading
from typing import AsyncGenerator

from neo4j import AsyncGraphDatabase
from neo4j._async.driver import AsyncDriver
from neo4j._async.work.session import AsyncSession

from app.core.config import settings

_driver: AsyncDriver | None = None
_lock = threading.Lock()


def _get_driver() -> AsyncDriver:
    """Get or create the shared Neo4j AsyncDriver (thread-safe, no event loop).

    Uses threading.Lock because asyncio.Lock would couple the driver's lifetime
    to the event loop that first created it, breaking reuse across test scopes.
    """
    global _driver
    if _driver is None:
        with _lock:
            if _driver is None:  # Double-check under lock
                _driver = AsyncGraphDatabase.driver(
                    settings.NEO4J_URI,
                    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                )
    return _driver


async def get_neo4j_session() -> AsyncGenerator[AsyncSession, None]:
    driver = _get_driver()
    async with driver.session() as session:
        yield session


async def check_neo4j_health() -> bool:
    """Health check using the shared driver — no extra driver creation."""
    try:
        driver = _get_driver()
        async with driver.session() as session:
            await session.run("RETURN 1")
        return True
    except Exception:
        return False


async def close_neo4j() -> None:
    global _driver
    with _lock:
        if _driver is not None:
            await _driver.close()
            _driver = None
