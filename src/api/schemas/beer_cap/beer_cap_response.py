from pydantic import ConfigDict, Field

from src.api.schemas.beer.beer_response_base import BeerResponseBase
from src.api.schemas.beer_cap.beer_cap_response_base import BeerCapResponseBase


class BeerCapResponseWithUrl(BeerCapResponseBase):
    """
    Full response schema for a beer cap, including its presigned image URL
    and associated beer information.
    """

    presigned_url: str = Field(
        ..., description="Temporary URL to access the beer cap image"
    )
    beer: BeerResponseBase = Field(..., description="Beer to which this cap belongs")

    model_config = ConfigDict(from_attributes=True, extra="forbid")
