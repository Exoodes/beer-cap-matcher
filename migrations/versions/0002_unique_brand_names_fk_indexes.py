"""unique beer brand names, indexes on foreign keys

Duplicate brand names are merged into the oldest brand first: brands only
carry a name, so repointing their beers loses nothing.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-17 12:40:00

"""

from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        WITH keep AS (
            SELECT name, MIN(id) AS keep_id
            FROM beer_brands
            GROUP BY name
            HAVING COUNT(*) > 1
        )
        UPDATE beers b
        SET beer_brand_id = keep.keep_id
        FROM beer_brands bb
        JOIN keep ON keep.name = bb.name
        WHERE b.beer_brand_id = bb.id AND bb.id <> keep.keep_id
        """
    )
    op.execute(
        """
        DELETE FROM beer_brands bb
        USING beer_brands older
        WHERE bb.name = older.name AND bb.id > older.id
        """
    )
    op.create_unique_constraint("beer_brands_name_key", "beer_brands", ["name"])

    op.create_index("ix_beers_beer_brand_id", "beers", ["beer_brand_id"])
    op.create_index("ix_beers_country_id", "beers", ["country_id"])
    op.create_index("ix_beer_caps_beer_id", "beer_caps", ["beer_id"])
    op.create_index("ix_augmented_caps_beer_cap_id", "augmented_caps", ["beer_cap_id"])


def downgrade() -> None:
    op.drop_index("ix_augmented_caps_beer_cap_id", table_name="augmented_caps")
    op.drop_index("ix_beer_caps_beer_id", table_name="beer_caps")
    op.drop_index("ix_beers_country_id", table_name="beers")
    op.drop_index("ix_beers_beer_brand_id", table_name="beers")
    op.drop_constraint("beer_brands_name_key", "beer_brands", type_="unique")
