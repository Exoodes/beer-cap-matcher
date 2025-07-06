from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BeerCapMetadataSchema(BaseModel):
    year: Optional[int] = Field(None, description="Year the cap was used or produced")
    # country: Optional[str] = Field(None, description="Country of origin")

    model_config = ConfigDict(from_attributes=True)


class BeerCapCreateSchema(BaseModel):
    filename: str = Field(..., description="File name of the beer cap image")
    metadata: BeerCapMetadataSchema

    model_config = ConfigDict(from_attributes=True)
