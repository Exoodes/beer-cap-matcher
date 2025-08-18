from sqlalchemy import Column, Date, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from src.db.entities import Base


class BeerCap(Base):
    """Represents a physical beer cap, including its variant and image.

    Linked to a specific Beer and may have multiple AugmentedCaps
    (e.g., cropped, processed versions for AI).
    """

    __tablename__ = "beer_caps"

    id = Column(Integer, primary_key=True, index=True)

    s3_key = Column(String, nullable=False, unique=True)
    variant_name = Column(String(255), nullable=True)
    collected_date = Column(Date, nullable=True)

    beer_id = Column(Integer, ForeignKey("beers.id"), nullable=False)
    beer = relationship("Beer", back_populates="caps")

    augmented_caps = relationship(
        "AugmentedCap", back_populates="beer_cap", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<BeerCap id={self.id} variant_name='{self.variant_name}' "
            f"beer_id={self.beer_id} s3_key='{self.s3_key}' "
            f"collected_date={self.collected_date}>"
        )

    def __str__(self) -> str:
        return f"BeerCap: {self.variant_name or 'N/A'} (ID: {self.id})"
