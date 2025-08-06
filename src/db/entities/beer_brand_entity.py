from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from src.db.entities import Base


class BeerBrand(Base):
    """Represents a beer brand which can have multiple beers.
    For example, "Bernard", "Staropramen", "Svijany", etc.
    """

    __tablename__ = "beer_brands"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)

    beers = relationship("Beer", back_populates="beer_brand")

    def __repr__(self) -> str:
        return f"<BeerBrand id={self.id} name='{self.name}'>"

    def __str__(self) -> str:
        return f"Beer Brand: {self.name} (ID: {self.id})"
