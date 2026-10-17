from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.entities import Base

if TYPE_CHECKING:
    from .beer_brand_entity import BeerBrand
    from .beer_cap_entity import BeerCap
    from .country_entity import Country


class Beer(Base):
    """Represents a type of beer in the database.

    Each Beer can have multiple associated BeerCaps.
    """

    __tablename__ = "beers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    country_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("countries.id"), nullable=True, index=True
    )
    beer_brand_id: Mapped[int] = mapped_column(
        ForeignKey("beer_brands.id"), nullable=False, index=True
    )

    country: Mapped[Optional["Country"]] = relationship(back_populates="beers")
    beer_brand: Mapped["BeerBrand"] = relationship(back_populates="beers")
    caps: Mapped[list["BeerCap"]] = relationship(back_populates="beer")

    __table_args__ = (
        CheckConstraint("rating >= 0 AND rating <= 10", name="rating_range"),
    )

    def __repr__(self) -> str:
        return (
            f"<Beer id={self.id} name='{self.name}' beer_brand_id={self.beer_brand_id}>"
        )

    def __str__(self) -> str:
        return f"Beer: {self.name} (ID: {self.id})"


# A brand can't have two beers with the same name (ignoring case).
Index(
    "uq_beers_brand_name_lower",
    Beer.beer_brand_id,
    func.lower(Beer.name),
    unique=True,
)
