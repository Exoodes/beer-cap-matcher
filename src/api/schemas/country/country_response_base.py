from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CountryResponseBase(BaseModel):
    """Base response schema for a country."""

    id: int = Field(..., description="Unique ID of the country")
    name: str = Field(..., description="Name of the country")
    description: Optional[str] = Field(None, description="Description of the country")

    model_config = ConfigDict(from_attributes=True, extra="forbid")
