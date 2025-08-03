from pydantic import ConfigDict

from src.api.schemas.beer.beer_response_base import BeerResponseBase
from src.api.schemas.beer_cap.beer_cap_response_base import BeerCapResponseBase


class BeerCapResponseWithUrl(BeerCapResponseBase):
    presigned_url: str
    beer: BeerResponseBase

    model_config = ConfigDict(from_attributes=True, extra="forbid")
