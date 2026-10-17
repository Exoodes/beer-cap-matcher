"""case-insensitive unique names for brands, countries and beers

Names are compared after trimming, collapsing inner whitespace and
lowercasing. Entries that only differ that way are merged into the oldest
one first: its beers (for brands and countries) or caps (for beers) move
over, then the duplicates are deleted. Brands go first, as merging them can
put two beers of the same name under one brand.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-17 21:00:00

"""

from typing import Sequence, Union

from alembic import op

revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CLEAN = r"regexp_replace(btrim(name), '\s+', ' ', 'g')"
KEY = f"lower({CLEAN})"


def _keep_ids(table: str, partition: str) -> str:
    """Rows paired with the oldest id among their duplicates."""
    return f"""
        SELECT id, MIN(id) OVER (PARTITION BY {partition}) AS keep_id
        FROM {table}
    """


def upgrade() -> None:
    for table, fk in (("beer_brands", "beer_brand_id"), ("countries", "country_id")):
        op.execute(
            f"""
            UPDATE beers SET {fk} = d.keep_id
            FROM ({_keep_ids(table, KEY)}) d
            WHERE beers.{fk} = d.id AND d.id <> d.keep_id
            """
        )
        op.execute(
            f"""
            DELETE FROM {table} t
            USING ({_keep_ids(table, KEY)}) d
            WHERE t.id = d.id AND d.id <> d.keep_id
            """
        )

    beer_partition = f"beer_brand_id, {KEY}"
    op.execute(
        f"""
        UPDATE beer_caps SET beer_id = d.keep_id
        FROM ({_keep_ids("beers", beer_partition)}) d
        WHERE beer_caps.beer_id = d.id AND d.id <> d.keep_id
        """
    )
    op.execute(
        f"""
        DELETE FROM beers b
        USING ({_keep_ids("beers", beer_partition)}) d
        WHERE b.id = d.id AND d.id <> d.keep_id
        """
    )

    for table in ("beer_brands", "countries", "beers"):
        op.execute(f"UPDATE {table} SET name = {CLEAN} WHERE name <> {CLEAN}")

    op.execute(
        "CREATE UNIQUE INDEX uq_beer_brands_name_lower ON beer_brands (lower(name))"
    )
    op.execute("CREATE UNIQUE INDEX uq_countries_name_lower ON countries (lower(name))")
    op.execute(
        "CREATE UNIQUE INDEX uq_beers_brand_name_lower "
        "ON beers (beer_brand_id, lower(name))"
    )


def downgrade() -> None:
    op.drop_index("uq_beers_brand_name_lower", table_name="beers")
    op.drop_index("uq_countries_name_lower", table_name="countries")
    op.drop_index("uq_beer_brands_name_lower", table_name="beer_brands")
