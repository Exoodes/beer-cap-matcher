from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.entities import Base

if TYPE_CHECKING:
    from .beer_entity import Beer


class BeerBrand(Base):
    """Represents a beer brand which can have multiple beers.
    For example, "Bernard", "Staropramen", "Svijany", etc.
    """

    __tablename__ = "beer_brands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    beers: Mapped[list["Beer"]] = relationship(back_populates="beer_brand")

    def __repr__(self) -> str:
        return f"<BeerBrand id={self.id} name='{self.name}'>"

    def __str__(self) -> str:
        return f"Beer Brand: {self.name} (ID: {self.id})"
