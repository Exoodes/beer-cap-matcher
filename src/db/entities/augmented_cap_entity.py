from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.entities import Base

if TYPE_CHECKING:
    from .beer_cap_entity import BeerCap


class AugmentedCap(Base):
    """Represents an augmented or processed version of a beer cap image,
    such as cropped, background-removed, or vectorized for ML.

    Linked to a BeerCap via a foreign key.
    """

    __tablename__ = "augmented_caps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    s3_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    embedding_vector: Mapped[Optional[list[float]]] = mapped_column(
        ARRAY(Float), nullable=True
    )

    beer_cap_id: Mapped[int] = mapped_column(
        ForeignKey("beer_caps.id", ondelete="CASCADE"), nullable=False
    )
    beer_cap: Mapped["BeerCap"] = relationship(back_populates="augmented_caps")

    def __repr__(self) -> str:
        return (
            f"<AugmentedCap id={self.id} beer_cap_id={self.beer_cap_id} "
            f"s3_key='{self.s3_key}' vector_len={len(self.embedding_vector) if self.embedding_vector else 0}>"
        )

    def __str__(self) -> str:
        return f"AugmentedCap: {self.s3_key} (ID: {self.id})"
