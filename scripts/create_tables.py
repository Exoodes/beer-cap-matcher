"""Applies database migrations.

Kept under this name because deployments run ``python -m scripts.create_tables``
on every start.
"""

from src.db.utils import run_migrations

if __name__ == "__main__":
    run_migrations()
