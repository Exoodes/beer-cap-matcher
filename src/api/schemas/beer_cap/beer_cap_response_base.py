from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BeerCapResponseBase(BaseModel):
    """
    Base schema for a beer cap, including its ID, optional variant name,
    and the date it was collected.
    """

    id: int = Field(..., description="Unique ID of the beer cap")
    variant_name: Optional[str] = Field(
        default=None,
        description="Variant name of the beer cap, if applicable",
    )
    collected_date: Optional[date] = Field(
        default=None,
        description="Date when this cap was collected",
    )

    model_config = ConfigDict(from_attributes=True, extra="forbid")
