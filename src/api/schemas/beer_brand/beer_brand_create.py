from pydantic import BaseModel, ConfigDict, Field

from src.api.schemas.common.names import CleanName


class BeerBrandCreateSchema(BaseModel):
    name: CleanName = Field(
        ..., min_length=1, max_length=100, description="Name of the beer brand"
    )

    model_config = ConfigDict(from_attributes=True, extra="forbid")
