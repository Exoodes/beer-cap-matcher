from typing import Optional

from pydantic import BaseModel, Field


class BeerCapMetadataSchema(BaseModel):
    year: Optional[int] = Field(None, description="Year the cap was used or produced")
    # country: Optional[str] = Field(None, description="Country of origin")

    class Config:
        from_attributes = True


class BeerCapCreateSchema(BaseModel):
    filename: str = Field(..., description="File name of the beer cap image")
    metadata: BeerCapMetadataSchema

    class Config:
        from_attributes = True
