from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import GLOBAL_ASYNC_SESSION_MAKER


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Asynchronous generator that provides a database session.

    This function is designed to be used as a dependency (e.g., in FastAPI)
    to manage the lifecycle of a database session. It creates a new session
    from the global session maker for each request and ensures that the
    session is properly closed after the request is handled.

    Yields:
        AsyncSession: An active SQLAlchemy asynchronous database session.
    """
    async with GLOBAL_ASYNC_SESSION_MAKER() as session:
        yield session
