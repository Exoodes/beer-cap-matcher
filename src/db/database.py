from typing import Tuple

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker

from src.config.settings import settings


def get_db_resources(
    database_url: str, echo: bool = False
) -> Tuple[AsyncEngine, sessionmaker]:

    engine = create_async_engine(database_url, echo=echo, future=True)
    async_session = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    return engine, async_session


GLOBAL_DATABASE_URL = settings.postgres_database_url
if not GLOBAL_DATABASE_URL:
    raise ValueError("POSTGRES_DATABASE_URL environment variable is not set.")

GLOBAL_ENGINE, GLOBAL_ASYNC_SESSION_MAKER = get_db_resources(GLOBAL_DATABASE_URL)
