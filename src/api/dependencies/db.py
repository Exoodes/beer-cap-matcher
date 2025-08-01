from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import GLOBAL_ASYNC_SESSION_MAKER


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with GLOBAL_ASYNC_SESSION_MAKER() as session:
        yield session
