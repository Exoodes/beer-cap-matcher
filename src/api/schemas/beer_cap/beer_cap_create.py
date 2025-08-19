# year: Optional[int] = Field(None, description="Year the cap was used or produced")
# country: Optional[str] = Field(None, description="Country of origin")

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BeerCapCreateSchema(BaseModel):
    """
    Schema for creating a new beer cap entry, including image filename
    and optional variant name.
    """

    filename: str = Field(
        ..., min_length=1, max_length=255, description="File name of the beer cap image"
    )
    variant_name: Optional[str] = Field(
        default=None, max_length=100, description="Variant name of the beer cap"
    )
    collected_date: Optional[date] = Field(
        default=None, description="Date when this cap was collected"
    )
    beer_id: Optional[int] = Field(
        default=None, description="ID of an existing beer to attach the cap to"
    )
    beer_name: Optional[str] = Field(
        default=None, description="Name of a new beer to create"
    )
    beer_brand_id: Optional[int] = Field(
        default=None, description="ID of an existing beer brand for a new beer"
    )
    beer_brand_name: Optional[str] = Field(
        default=None, description="Name of a new beer brand for a new beer"
    )
    country_id: Optional[int] = Field(
        default=None, description="ID of an existing country for a new beer"
    )
    country_name: Optional[str] = Field(
        default=None, description="Name of a new country for a new beer"
    )

    @field_validator("beer_brand_id", "beer_brand_name", "country_id", "country_name")
    @classmethod
    def validate_new_beer_fields(cls, v: str | int, info) -> str | int:
        if info.data.get("beer_id") is None and info.data.get("beer_name") is not None:
            if info.field_name in ["beer_brand_id", "beer_brand_name"] and v is None:
                raise ValueError(
                    "beer_brand_id or beer_brand_name must be provided for a new beer"
                )
        return v

    model_config = ConfigDict(from_attributes=True)
