from typing import Optional

from pydantic import Field

from src.api.schemas.beer.beer_response_base import BeerResponseBase
from src.api.schemas.country.country_response_base import CountryResponseBase


class CountryResponseWithBeers(CountryResponseBase):
    """Response schema for a country that includes its beers."""

    beers: Optional[list[BeerResponseBase]] = Field(
        default=None, description="List of beers produced in this country"
    )
