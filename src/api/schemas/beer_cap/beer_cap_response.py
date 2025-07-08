from typing import Optional

from pydantic import BaseModel, ConfigDict


class BeerResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class BeerCapResponse(BaseModel):
    id: int
    variant_name: Optional[str] = None
    presigned_url: str
    beer: BeerResponse

    model_config = ConfigDict(from_attributes=True, extra="forbid")
