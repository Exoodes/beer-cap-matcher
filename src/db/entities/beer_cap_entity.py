from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.entities import Base

if TYPE_CHECKING:
    from .augmented_cap_entity import AugmentedCap
    from .beer_entity import Beer


class BeerCap(Base):
    """Represents a physical beer cap, including its variant and image.

    Linked to a specific Beer and may have multiple AugmentedCaps
    (e.g., cropped, processed versions for AI).
    """

    __tablename__ = "beer_caps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    s3_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    variant_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    collected_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    beer_id: Mapped[int] = mapped_column(ForeignKey("beers.id"), nullable=False)
    beer: Mapped["Beer"] = relationship(back_populates="caps")

    augmented_caps: Mapped[list["AugmentedCap"]] = relationship(
        back_populates="beer_cap",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<BeerCap id={self.id} variant_name='{self.variant_name}' "
            f"beer_id={self.beer_id} s3_key='{self.s3_key}' "
            f"collected_date={self.collected_date}>"
        )

    def __str__(self) -> str:
        return f"BeerCap: {self.variant_name or 'N/A'} (ID: {self.id})"
