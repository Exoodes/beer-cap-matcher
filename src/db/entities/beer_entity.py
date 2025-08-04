from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from src.db.entities import Base


class Beer(Base):
    """Represents a type of beer in the database.

    Each Beer can have multiple associated BeerCaps.
    """

    __tablename__ = "beers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)

    caps = relationship("BeerCap", back_populates="beer")

    def __repr__(self) -> str:
        return f"<Beer id={self.id} name='{self.name}'>"

    def __str__(self) -> str:
        return f"Beer: {self.name} (ID: {self.id})"
