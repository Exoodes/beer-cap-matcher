from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship

from . import Base


class Country(Base):
    """Database model for a country."""

    __tablename__ = "countries"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)

    beers = relationship("Beer", back_populates="country")

    def __repr__(self) -> str:  # pragma: no cover - simple repr
        return f"<Country id={self.id} name='{self.name}'>"
