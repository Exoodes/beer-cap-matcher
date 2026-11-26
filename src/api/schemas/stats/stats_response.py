from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class GrowthPoint(BaseModel):
    """The collection's size at the end of one month of collected dates."""

    month: str = Field(..., description="The month, YYYY-MM")
    total: int = Field(..., description="Caps collected up to the month's end")


class NewestCap(BaseModel):
    """One of the caps entered last."""

    id: int
    beer: str = Field(..., description="Name of the cap's beer")
    thumbnail_url: str = Field(
        ..., description="Small image (the full image if no thumbnail exists)"
    )
    collected_date: Optional[date] = Field(
        ..., description="When the cap was collected, if known"
    )


class CountryCount(BaseModel):
    """Caps from one country."""

    country: str
    caps: int


class StatsResponse(BaseModel):
    """Counts over the whole collection, for dashboards."""

    caps: int
    beers: int = Field(..., description="Beers with at least one cap")
    brands: int = Field(..., description="Brands of those beers")
    countries: int = Field(..., description="Countries of those beers")
    collected_this_month: int = Field(
        ..., description="Caps collected in the current month (Prague time)"
    )
    growth: list[GrowthPoint] = Field(
        ...,
        description="Running total per month, from the first collected month to "
        "this one; caps without a date are left out",
    )
    undated: int = Field(..., description="Caps without a collected date")
    newest: list[NewestCap] = Field(
        ..., description="The last caps entered, newest first"
    )
    cap_ids: list[int] = Field(..., description="Every cap's ID, ascending")
    by_country: list[CountryCount] = Field(
        ...,
        description="Caps per country, most first; beers without a country "
        "are left out",
    )
