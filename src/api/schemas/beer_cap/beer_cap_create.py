from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BeerCapCreateSchema(BaseModel):
    filename: str = Field(..., description="File name of the beer cap image")

    # year: Optional[int] = Field(None, description="Year the cap was used or produced")
    # country: Optional[str] = Field(None, description="Country of origin")
    variant_name: Optional[str] = Field(None, description="Variant name of the beer cap")

    model_config = ConfigDict(from_attributes=True)
