from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BeerBrandUpdateSchema(BaseModel):
    name: Optional[str] = Field(
        default=None, min_length=1, max_length=100, description="Updated name of the beer brand"
    )

    model_config = ConfigDict(from_attributes=True, extra="forbid")
