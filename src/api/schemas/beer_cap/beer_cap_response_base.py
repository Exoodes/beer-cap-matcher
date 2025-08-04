from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BeerCapResponseBase(BaseModel):
    """
    Base schema for a beer cap, including its ID and optional variant name.
    """

    id: int = Field(..., description="Unique ID of the beer cap")
    variant_name: Optional[str] = Field(
        default=None,
        description="Variant name of the beer cap, if applicable"
    )

    model_config = ConfigDict(from_attributes=True, extra="forbid")
