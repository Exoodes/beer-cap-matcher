# year: Optional[int] = Field(None, description="Year the cap was used or produced")
# country: Optional[str] = Field(None, description="Country of origin")

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BeerCapCreateSchema(BaseModel):
    """
    Schema for creating a new beer cap entry, including image filename and optional variant name.
    """

    filename: str = Field(
        ..., min_length=1, max_length=255, description="File name of the beer cap image"
    )
    variant_name: Optional[str] = Field(
        default=None, max_length=100, description="Variant name of the beer cap"
    )
    collected_date: Optional[date] = Field(
        default=None, description="Date when this cap was collected"
    )

    model_config = ConfigDict(from_attributes=True)
