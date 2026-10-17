from typing import Optional

from pydantic import ConfigDict, Field

from src.api.schemas.common.partial_update import PartialUpdateSchema


class BeerBrandUpdateSchema(PartialUpdateSchema):
    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Updated name of the beer brand",
    )

    non_nullable_fields = ("name",)

    model_config = ConfigDict(from_attributes=True, extra="forbid")
