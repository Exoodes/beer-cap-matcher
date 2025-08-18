from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Typed declarative base for SQLAlchemy 2.0."""

    pass


from .augmented_cap_entity import AugmentedCap  # noqa: E402
from .beer_brand_entity import BeerBrand  # noqa: E402
from .beer_cap_entity import BeerCap  # noqa: E402
from .beer_entity import Beer  # noqa: E402
from .country_entity import Country  # noqa: E402

__all__ = ["Base", "Beer", "BeerCap", "AugmentedCap", "BeerBrand", "Country"]
