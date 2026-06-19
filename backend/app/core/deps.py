from typing import AsyncGenerator

from neo4j._async.work.session import AsyncSession

from app.graph.client import get_neo4j_session


async def get_db_neo4j() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_neo4j_session():
        yield session
