from typing import Optional

from pydantic import BaseModel, ConfigDict


class BeerCapResponse(BaseModel):
    id: int
    beer_id: int
    variant_name: Optional[str] = None
    presigned_url: str

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class BeerCapCreateExisting(BaseModel):
    beer_id: int
    variant_name: Optional[str] = None


class BeerCapCreateWithBeer(BaseModel):
    beer_name: str
    variant_name: Optional[str] = None
