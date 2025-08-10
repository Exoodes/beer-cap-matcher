from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BeerCreateSchema(BaseModel):
    """Schema for creating a new beer entity."""

    name: str = Field(..., min_length=1, max_length=100, description="Name of the beer")
    beer_brand_id: int = Field(..., ge=1, description="ID of the beer brand to which this beer belongs")
    rating: Optional[int] = Field(default=0, ge=0, le=10, description="Rating of the beer (0-10)")
    country_id: Optional[int] = Field(default=None, description="ID of the associated country")

    model_config = ConfigDict(from_attributes=True, extra="forbid")
