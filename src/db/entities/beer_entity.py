from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from src.db.entities import Base


class Beer(Base):
    """Represents a type of beer in the database.

    Each Beer can have multiple associated BeerCaps.
    """

    __tablename__ = "beers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    beer_brand_id = Column(Integer, ForeignKey("beer_brands.id"), nullable=False)

    beer_brand = relationship("BeerBrand", back_populates="beers")
    caps = relationship("BeerCap", back_populates="beer")

    def __repr__(self) -> str:
        return f"<Beer id={self.id} name='{self.name}' beer_brand_id={self.beer_brand_id}>"

    def __str__(self) -> str:
        return f"Beer: {self.name} (ID: {self.id})"
