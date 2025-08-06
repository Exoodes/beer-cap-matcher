from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BeerBrandResponseBase(BaseModel):
    id: int = Field(..., description="Unique ID of the beer brand")
    name: str = Field(..., description="Name of the beer brand")

    model_config = ConfigDict(from_attributes=True, extra="forbid")
