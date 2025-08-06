from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from src.api.schemas.country.country_response_base import CountryResponseBase


class BeerResponseBase(BaseModel):
    """
    Base response schema for a beer entity, containing basic beer info.
    """

    id: int = Field(..., description="Unique ID of the beer")
    name: str = Field(..., description="Name of the beer")
    country: Optional[CountryResponseBase] = Field(
        default=None, description="Country where the beer is produced"
    )

    model_config = ConfigDict(from_attributes=True, extra="forbid")
