from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from src.db.entities import Base


class BeerCap(Base):
    __tablename__ = "beer_caps"

    id = Column(Integer, primary_key=True, index=True)

    s3_key = Column(String, nullable=False, unique=True)
    variant_name = Column(String(255), nullable=True)

    beer_id = Column(Integer, ForeignKey("beers.id"), nullable=False)
    beer = relationship("Beer", back_populates="caps")

    augmented_caps = relationship("AugmentedCap", back_populates="beer_cap", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<BeerCap id={self.id} variant={self.variant_name} beer_id={self.beer_id}>"
