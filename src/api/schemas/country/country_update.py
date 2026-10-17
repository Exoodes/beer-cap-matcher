from typing import Optional

from pydantic import ConfigDict, Field

from src.api.schemas.common.partial_update import PartialUpdateSchema


class CountryUpdateSchema(PartialUpdateSchema):
    """Schema for updating an existing country."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None)

    non_nullable_fields = ("name",)

    model_config = ConfigDict(from_attributes=True, extra="forbid")
