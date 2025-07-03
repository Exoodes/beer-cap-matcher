from sqlalchemy import Column, Integer, String, Text

from src.models import Base


class Beer(Base):
    __tablename__ = "beers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    brewery = Column(String(255), nullable=True)
    style = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Beer id={self.id} name={self.name}>"
