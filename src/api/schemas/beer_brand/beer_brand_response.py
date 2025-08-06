from typing import List, Optional

from pydantic import Field

from src.api.schemas.beer.beer_response_base import BeerResponseBase
from src.api.schemas.beer_brand.beer_brand_response_base import BeerBrandResponseBase


class BeerBrandResponseWithBeers(BeerBrandResponseBase):
    beers: Optional[List[BeerResponseBase]] = Field(
        default=None,
        description="List of beers produced by this beer brand",
    )
