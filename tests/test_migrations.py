"""Migration tests, run against a throwaway database next to the test DB."""

import asyncio
from collections.abc import Generator

import asyncpg  # type: ignore[import-untyped]
import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from src.db.entities import Base
from src.db.utils import ALEMBIC_INI, run_migrations
from tests.conftest import TEST_POSTGRES_DATABASE_URL

assert TEST_POSTGRES_DATABASE_URL
MIGRATION_DB = "beercap_migration_test"
MIGRATION_DB_URL = (
    make_url(TEST_POSTGRES_DATABASE_URL)
    .set(database=MIGRATION_DB)
    .render_as_string(hide_password=False)
)


async def _recreate_database() -> None:
    admin_url = make_url(TEST_POSTGRES_DATABASE_URL).set(drivername="postgresql")
    conn = await asyncpg.connect(admin_url.render_as_string(hide_password=False))
    try:
        await conn.execute(f'DROP DATABASE IF EXISTS "{MIGRATION_DB}" WITH (FORCE)')
        await conn.execute(f'CREATE DATABASE "{MIGRATION_DB}"')
    finally:
        await conn.close()


async def _execute(*statements: str) -> list[list[tuple]]:
    engine = create_async_engine(MIGRATION_DB_URL)
    results = []
    try:
        async with engine.begin() as conn:
            for stmt in statements:
                result = await conn.execute(text(stmt))
                results.append(list(result.tuples()) if result.returns_rows else [])
    finally:
        await engine.dispose()
    return results


async def _schema_diff() -> list:
    engine = create_async_engine(MIGRATION_DB_URL)
    try:
        async with engine.connect() as conn:
            return await conn.run_sync(
                lambda c: compare_metadata(MigrationContext.configure(c), Base.metadata)
            )
    finally:
        await engine.dispose()


@pytest.fixture
def empty_database() -> Generator[None, None, None]:
    asyncio.run(_recreate_database())
    yield


def test_migrations_build_the_model_schema(empty_database: None) -> None:
    run_migrations(MIGRATION_DB_URL)

    assert asyncio.run(_schema_diff()) == []


def test_legacy_database_is_stamped_and_duplicate_brands_merged(
    empty_database: None,
) -> None:
    # Recreate a pre-migration database: the baseline schema without the
    # alembic_version table, as create_all used to leave it.
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", MIGRATION_DB_URL)
    command.upgrade(config, "0001")
    asyncio.run(
        _execute(
            "DROP TABLE alembic_version",
            "INSERT INTO beer_brands (id, name) VALUES (1, 'Bernard'), (2, 'Bernard')",
            "INSERT INTO beers (name, rating, beer_brand_id) VALUES ('A', 0, 1), "
            "('B', 0, 2)",
        )
    )

    run_migrations(MIGRATION_DB_URL)
    run_migrations(MIGRATION_DB_URL)  # idempotent

    version, brands, beer_brand_ids = asyncio.run(
        _execute(
            "SELECT version_num FROM alembic_version",
            "SELECT id, name FROM beer_brands",
            "SELECT DISTINCT beer_brand_id FROM beers",
        )
    )
    assert version == [(ScriptDirectory.from_config(config).get_current_head(),)]
    assert brands == [(1, "Bernard")]
    assert beer_brand_ids == [(1,)]
    assert asyncio.run(_schema_diff()) == []


def test_partial_legacy_schema_is_refused(empty_database: None) -> None:
    asyncio.run(_execute("CREATE TABLE beer_brands (id serial primary key)"))

    with pytest.raises(RuntimeError, match="partial pre-migration schema"):
        run_migrations(MIGRATION_DB_URL)


def test_names_differing_in_case_or_spacing_are_merged(empty_database: None) -> None:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", MIGRATION_DB_URL)
    command.upgrade(config, "0003")
    asyncio.run(
        _execute(
            "INSERT INTO countries (id, name) VALUES (1, 'Česko'), (2, ' česko ')",
            "INSERT INTO beer_brands (id, name) VALUES (1, 'Bernard'), "
            "(2, 'bernard  ')",
            "INSERT INTO beers (id, name, rating, beer_brand_id, country_id) VALUES "
            "(1, 'Bernard 12°', 0, 1, 1), (2, 'bernard   12°', 0, 2, 2), "
            "(3, 'Bernard  11°', 0, 2, 2)",
            "INSERT INTO beer_caps (id, s3_key, beer_id) VALUES "
            "(1, 'a.jpg', 1), (2, 'b.jpg', 2), (3, 'c.jpg', 3)",
        )
    )

    run_migrations(MIGRATION_DB_URL)

    countries, brands, beers, caps = asyncio.run(
        _execute(
            "SELECT id, name FROM countries",
            "SELECT id, name FROM beer_brands",
            "SELECT id, name, beer_brand_id, country_id FROM beers ORDER BY id",
            "SELECT id, beer_id FROM beer_caps ORDER BY id",
        )
    )
    assert countries == [(1, "Česko")]
    assert brands == [(1, "Bernard")]
    assert beers == [(1, "Bernard 12°", 1, 1), (3, "Bernard 11°", 1, 1)]
    assert caps == [(1, 1), (2, 1), (3, 3)]
    assert asyncio.run(_schema_diff()) == []
