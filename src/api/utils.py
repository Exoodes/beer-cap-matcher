from src.api.schemas.beer.beer_response_base import BeerResponseBase
from src.api.schemas.beer_cap.beer_cap_response import BeerCapResponseWithUrl
from src.db.entities.beer_cap_entity import BeerCap
from src.services.beer_cap_facade import BeerCapFacade


def build_beer_cap_response(
    beer_cap: BeerCap, facade: BeerCapFacade
) -> BeerCapResponseWithUrl:
    """Create a :class:`BeerCapResponseWithUrl` for the given beer cap.

    Args:
        beer_cap: BeerCap entity with its related Beer loaded.
        facade: Facade used to generate presigned URLs for cap images.

    Returns:
        BeerCapResponseWithUrl including a presigned image URL and associated beer data.
    """

    url = facade.get_presigned_url_for_cap(beer_cap.s3_key)
    beer_response = BeerResponseBase(
        id=beer_cap.beer_id,
        name=beer_cap.beer.name,
        rating=beer_cap.beer.rating,
    )

    return BeerCapResponseWithUrl(
        id=beer_cap.id,
        variant_name=beer_cap.variant_name,
        collected_date=beer_cap.collected_date,
        presigned_url=url,
        beer=beer_response,
    )


__all__ = ["build_beer_cap_response"]
