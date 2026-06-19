from typing import AsyncGenerator

from neo4j import AsyncGraphDatabase
from neo4j._async.driver import AsyncDriver
from neo4j._async.work.session import AsyncSession

from app.core.config import settings

_driver: AsyncDriver | None = None


def _get_driver() -> AsyncDriver:
    global _driver
    if _driver is None:
        _driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
    return _driver


async def get_neo4j_session() -> AsyncGenerator[AsyncSession, None]:
    driver = _get_driver()
    async with driver.session() as session:
        yield session


async def close_neo4j() -> None:
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None
