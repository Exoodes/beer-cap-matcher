from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from src.database import Base


class AugmentedCap(Base):
    __tablename__ = "augmented_caps"

    id = Column(Integer, primary_key=True, index=True)
    beer_cap_id = Column(Integer, ForeignKey("beer_caps.id"), nullable=False)
    s3_key = Column(String, nullable=False, unique=True)
    embedding_vector = Column(String, nullable=True)

    beer_cap = relationship("BeerCap", back_populates="augmented_caps")
