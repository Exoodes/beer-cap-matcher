from typing import List, Optional

from pydantic import Field

from src.api.schemas.beer.beer_response_base import BeerResponseBase
from src.api.schemas.beer_cap.beer_cap_response_base import BeerCapResponseBase


class BeerResponseWithCaps(BeerResponseBase):
    """
    Extended response schema for a beer entity that includes a list of its caps.
    """

    caps: Optional[List[BeerCapResponseBase]] = Field(
        default=None, description="List of caps associated with this beer"
    )
