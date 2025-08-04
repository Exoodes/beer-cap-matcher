from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BeerUpdateSchema(BaseModel):
    """
    Schema for updating an existing beer entity.
    Only fields that should be changed need to be included.
    """

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Updated name of the beer"
    )

    model_config = ConfigDict(from_attributes=True, extra="forbid")
