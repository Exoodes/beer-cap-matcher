from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class BeerCapShortResponse(BaseModel):
    id: int
    variant_name: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class BeerResponseWithCaps(BaseModel):
    id: int
    name: str
    caps: Optional[List[BeerCapShortResponse]] = None

    model_config = ConfigDict(from_attributes=True)
