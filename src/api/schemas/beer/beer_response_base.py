from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from src.api.schemas.beer_brand.beer_brand_response_base import BeerBrandResponseBase
from src.api.schemas.country.country_response_base import CountryResponseBase


class BeerResponseBase(BaseModel):
    """
    Base response schema for a beer entity, containing basic beer info.
    """

    id: int = Field(..., description="Unique ID of the beer")
    name: str = Field(..., description="Name of the beer")
    rating: Optional[int] = Field(
        None, ge=0, le=10, description="Rating of the beer (0-10)"
    )
    country: Optional[CountryResponseBase] = Field(
        default=None, description="Country where the beer is produced"
    )
    beer_brand: Optional[BeerBrandResponseBase] = Field(
        default=None, description="Brand of the beer"
    )

    model_config = ConfigDict(from_attributes=True, extra="ignore")
