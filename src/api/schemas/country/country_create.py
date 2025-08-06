from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CountryCreateSchema(BaseModel):
    """Schema for creating a new country."""

    name: str = Field(..., min_length=1, max_length=100, description="Name of the country")
    description: Optional[str] = Field(
        default=None, description="Description of the country"
    )

    model_config = ConfigDict(from_attributes=True, extra="forbid")
