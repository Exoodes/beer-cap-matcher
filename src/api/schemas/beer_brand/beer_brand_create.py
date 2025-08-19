from pydantic import BaseModel, ConfigDict, Field


class BeerBrandCreateSchema(BaseModel):
    name: str = Field(
        ..., min_length=1, max_length=100, description="Name of the beer brand"
    )

    model_config = ConfigDict(from_attributes=True, extra="forbid")
