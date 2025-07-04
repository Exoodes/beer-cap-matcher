from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from src.models import Base


class Beer(Base):
    __tablename__ = "beers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)

    caps = relationship("BeerCap", back_populates="beer")

    def __repr__(self):
        return f"<Beer id={self.id} name={self.name}>"
