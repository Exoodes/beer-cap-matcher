from typing import List, Optional

from src.api.schemas.beer.beer_response_base import BeerResponseBase
from src.api.schemas.beer_cap.beer_cap_response_base import BeerCapResponseBase


class BeerResponseWithCaps(BeerResponseBase):
    caps: Optional[List[BeerCapResponseBase]] = None
