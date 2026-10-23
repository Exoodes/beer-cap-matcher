"""backfill missing collected dates

The first caps were imported without a collected date. They get
2026-01-01, so stats over collected dates count every cap.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-23 22:00:00

"""

from typing import Sequence, Union

from alembic import op

revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BACKFILL_DATE = "2026-01-01"


def upgrade() -> None:
    op.execute(
        f"UPDATE beer_caps SET collected_date = DATE '{BACKFILL_DATE}' "
        "WHERE collected_date IS NULL"
    )


def downgrade() -> None:
    # Which dates were backfilled isn't recorded, so nothing is undone.
    pass
