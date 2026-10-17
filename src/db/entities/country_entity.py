from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.entities import Base

if TYPE_CHECKING:
    from .beer_entity import Beer


class Country(Base):
    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Never null out beers' country on delete; the FK refuses deleting a country in use.
    beers: Mapped[list["Beer"]] = relationship(
        back_populates="country", passive_deletes="all"
    )

    def __repr__(self) -> str:
        return f"<Country id={self.id} name='{self.name}'>"


# Unique ignoring case too: "česká republika" can't sit next to "Česká Republika".
Index("uq_countries_name_lower", func.lower(Country.name), unique=True)
