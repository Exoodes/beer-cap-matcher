from typing import Optional

from pydantic import BaseModel


class BeerCapResponse(BaseModel):
    id: int
    beer_id: int
    variant_name: Optional[str]
    s3_key: str
    presigned_url: str

    class Config:
        from_attributes = True


class BeerCapCreateExisting(BaseModel):
    beer_id: int
    variant_name: Optional[str] = None


class BeerCapCreateWithBeer(BaseModel):
    beer_name: str
    variant_name: Optional[str] = None
