from typing import List, Optional

from pydantic import Field

from src.api.schemas.beer.beer_response_base import BeerResponseBase
from src.api.schemas.country.country_response_base import CountryResponseBase


class CountryResponseWithBeers(CountryResponseBase):
    """Response schema for a country that includes its beers."""

    beers: Optional[List[BeerResponseBase]] = Field(
        default=None, description="List of beers produced in this country"
    )
