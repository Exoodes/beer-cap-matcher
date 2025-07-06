from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from src.models import Base


class AugmentedCap(Base):
    __tablename__ = "augmented_caps"

    id = Column(Integer, primary_key=True, index=True)

    s3_key = Column(String, nullable=False, unique=True)
    embedding_vector = Column(String, nullable=True)

    beer_cap_id = Column(Integer, ForeignKey("beer_caps.id", ondelete="CASCADE"), nullable=False)
    beer_cap = relationship("BeerCap", back_populates="augmented_caps")

    def __repr__(self):
        return f"<AugmentedCap id={self.id} beer_cap_id={self.beer_cap_id}>"
