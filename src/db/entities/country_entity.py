from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.entities import Base

if TYPE_CHECKING:
    from .beer_entity import Beer


class Country(Base):
    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    beers: Mapped[list["Beer"]] = relationship(back_populates="country")

    def __repr__(self) -> str:
        return f"<Country id={self.id} name='{self.name}'>"
