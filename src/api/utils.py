from datetime import date
from typing import Optional, cast

from src.api.schemas.beer_brand.beer_brand_response import BeerBrandResponseBase
from src.api.schemas.country.country_response import CountryResponseBase
from src.api.schemas.beer.beer_response_base import BeerResponseBase
from src.api.schemas.beer_cap.beer_cap_response import BeerCapResponseWithUrl
from src.db.entities.beer_cap_entity import BeerCap
from src.services.beer_cap_facade import BeerCapFacade


def build_beer_cap_response(
    beer_cap: BeerCap, facade: BeerCapFacade
) -> BeerCapResponseWithUrl:
    url = facade.get_presigned_url_for_cap(beer_cap.s3_key)

    beer_response = BeerResponseBase(
        id=beer_cap.beer_id,
        name=beer_cap.beer.name,
        rating=beer_cap.beer.rating,
        country=(
            CountryResponseBase.model_validate(beer_cap.beer.country)
            if beer_cap.beer.country
            else None
        ),
        beer_brand=(
            BeerBrandResponseBase.model_validate(beer_cap.beer.beer_brand)
            if beer_cap.beer.beer_brand
            else None
        ),
    )

    return BeerCapResponseWithUrl(
        id=beer_cap.id,
        variant_name=beer_cap.variant_name,
        collected_date=cast(Optional[date], beer_cap.collected_date),
        presigned_url=url,
        beer=beer_response,
    )


__all__ = ["build_beer_cap_response"]
