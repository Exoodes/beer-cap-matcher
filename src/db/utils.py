import asyncio
from pathlib import Path
from typing import Optional

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"
BASELINE_REVISION = "0001"
BASELINE_TABLES = {"beer_brands", "countries", "beers", "beer_caps", "augmented_caps"}


async def _existing_tables(database_url: str) -> set[str]:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as conn:
            names = await conn.run_sync(lambda c: inspect(c).get_table_names())
    finally:
        await engine.dispose()
    return set(names)


def run_migrations(database_url: Optional[str] = None) -> None:
    """Brings the database schema up to date with Alembic.

    Databases created before migrations existed (via ``create_all``) have the
    baseline tables but no ``alembic_version``; they are stamped at the
    baseline revision first so only the later migrations run.

    Must be called outside a running event loop (Alembic's env.py uses
    ``asyncio.run``).

    Args:
        database_url: Database to migrate. Defaults to the app's database.

    Raises:
        RuntimeError: If the database has only some of the baseline tables.
    """
    url = database_url or settings.postgres_database_url
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))

    tables = asyncio.run(_existing_tables(url))
    if "alembic_version" not in tables and tables & BASELINE_TABLES:
        missing = BASELINE_TABLES - tables
        if missing:
            raise RuntimeError(
                f"Database has a partial pre-migration schema (missing: "
                f"{sorted(missing)}); refusing to stamp it."
            )
        logger.info("Existing schema without migrations found; stamping baseline.")
        command.stamp(config, BASELINE_REVISION)

    command.upgrade(config, "head")
    logger.info("Database schema is up to date.")
