from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BeerCapCreateSchema(BaseModel):
    """Schema for creating a new beer cap.

    Requires an image ``filename``. Optional fields allow setting a
    ``variant_name``, ``collected_date``, and linking the cap to an
    existing beer via ``beer_id`` or defining a new beer with
    ``beer_name``, ``beer_brand_id``/``beer_brand_name``, and
    ``country_id``/``country_name``.
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
        default=None,
        description=(
            "ID of an existing beer to attach the cap to; mutually exclusive with"
            " beer_name"
        ),
    )
    beer_name: Optional[str] = Field(
        default=None,
        description=("Name of a new beer to create; mutually exclusive with beer_id"),
    )
    rating: Optional[int] = Field(
        default=0, ge=0, le=10, description="Rating of the beer (0-10)"
    )
    beer_brand_id: Optional[int] = Field(
        default=None,
        description="ID of an existing beer brand when creating a new beer",
    )
    beer_brand_name: Optional[str] = Field(
        default=None,
        description="Name of a new beer brand when creating a new beer",
    )
    country_id: Optional[int] = Field(
        default=None,
        description="ID of an existing country when creating a new beer",
    )
    country_name: Optional[str] = Field(
        default=None,
        description="Name of a new country when creating a new beer",
    )

    @model_validator(mode="after")
    def validate_new_beer_fields(self):
        if self.beer_id is None and self.beer_name is not None:

            if self.beer_brand_id is None and self.beer_brand_name is None:
                raise ValueError(
                    "beer_brand_id or beer_brand_name must be provided for a new beer"
                )

            if self.country_id is None and self.country_name is None:
                raise ValueError(
                    "country_id or country_name must be provided for a new beer"
                )

        return self

    model_config = ConfigDict(from_attributes=True)
