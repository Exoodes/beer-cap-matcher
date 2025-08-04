from pydantic import BaseModel, ConfigDict, Field


class BeerResponseBase(BaseModel):
    """
    Base response schema for a beer entity, containing basic beer info.
    """

    id: int = Field(..., description="Unique ID of the beer")
    name: str = Field(..., description="Name of the beer")

    model_config = ConfigDict(from_attributes=True, extra="forbid")
