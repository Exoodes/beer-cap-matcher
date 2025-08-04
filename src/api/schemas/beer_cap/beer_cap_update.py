from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BeerCapUpdateSchema(BaseModel):
    """
    Schema for updating a beer cap's variant name or associated beer ID.
    """

    variant_name: Optional[str] = Field(
        default=None, max_length=100, description="Updated variant name of the beer cap"
    )
    beer_id: Optional[int] = Field(
        default=None, description="New beer ID to associate with this cap"
    )

    model_config = ConfigDict(from_attributes=True, extra="forbid")
