from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BeerUpdateSchema(BaseModel):
    """
    Schema for updating an existing beer entity.
    Only fields that should be changed need to be included.
    """

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Updated name of the beer",
    )
    country_id: Optional[int] = Field(
        default=None, description="ID of the associated country"
    )

    beer_brand_id: Optional[int] = Field(
        default=None,
        description="ID of the beer brand to which this beer belongs"
    )

    model_config = ConfigDict(from_attributes=True, extra="forbid")
