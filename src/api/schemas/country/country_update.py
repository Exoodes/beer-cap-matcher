from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CountryUpdateSchema(BaseModel):
    """Schema for updating an existing country."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None)

    model_config = ConfigDict(from_attributes=True, extra="forbid")
