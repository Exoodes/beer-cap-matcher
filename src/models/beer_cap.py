from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from src.models import Base


class BeerCap(Base):
    __tablename__ = "beer_caps"

    id = Column(Integer, primary_key=True, index=True)
    image_path = Column(String(512), nullable=False)
    variant_name = Column(String(255), nullable=True)
    special_edition = Column(Boolean, default=False)

    beer_id = Column(Integer, ForeignKey("beers.id"), nullable=False)

    beer = relationship("Beer", backref="caps")
    augmented_caps = relationship("AugmentedCap", back_populates="beer_cap")

    def __repr__(self):
        return f"<BeerCap id={self.id} variant={self.variant_name} beer_id={self.beer_id}>"
