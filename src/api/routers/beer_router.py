from fastapi import APIRouter, HTTPException
from fastapi.params import Query

from src.api.schemas.beer.beer_response import BeerCapShortResponse, BeerResponseWithCaps
from src.api.schemas.beer.update_schema import BeerUpdateSchema
from src.api.schemas.common.delete_status_response import DeleteStatusResponse
from src.db.crud.beer import get_all_beers, get_beer_by_id, update_beer
from src.db.database import GLOBAL_ASYNC_SESSION_MAKER
from src.facades.beer_cap_facade import BeerCapFacade
from src.storage.minio_client import MinioClientWrapper

router = APIRouter(prefix="/beers", tags=["Beers"])

minio_client = MinioClientWrapper()
beer_cap_facade = BeerCapFacade(minio_client)


@router.get("/caps", response_model=list[BeerResponseWithCaps])
async def get_all_beer_caps(
    include_caps: bool = Query(False, description="Include caps for each beer"),
):
    """
    Get all beer caps with their associated beers.
    """
    async with GLOBAL_ASYNC_SESSION_MAKER() as session:
        beers = await get_all_beers(session, load_caps=include_caps)

    result = []
    for beer in beers:
        if include_caps:
            caps = [BeerCapShortResponse(id=cap.id, variant_name=cap.variant_name) for cap in beer.caps]
        else:
            caps = None

        beer_response = BeerResponseWithCaps(id=beer.id, name=beer.name, caps=caps)
        result.append(beer_response)

    return result


@router.get("/{beer_id}", response_model=BeerResponseWithCaps)
async def api_get_beer_by_id(beer_id: int, include_caps: bool = Query(False, description="Include caps for the beer")):
    """
    Get a specific beer by its ID, optionally including its caps.
    """
    async with GLOBAL_ASYNC_SESSION_MAKER() as session:
        beer = await get_beer_by_id(session, beer_id, load_caps=include_caps)

    if not beer:
        raise HTTPException(status_code=404, detail="Beer not found.")

    if include_caps:
        caps = [BeerCapShortResponse(id=cap.id, variant_name=cap.variant_name) for cap in beer.caps]
    else:
        caps = None

    return BeerResponseWithCaps(id=beer.id, name=beer.name, caps=caps)


@router.delete("/{beer_id}", response_model=DeleteStatusResponse)
async def api_delete_beer(beer_id: int):
    """
    Delete a beer by its ID.
    """
    deleted = await beer_cap_facade.delete_beer_and_caps(beer_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Beer not found.")

    return DeleteStatusResponse(success=True, message="Beer deleted successfully.")


@router.patch("/{beer_id}", response_model=BeerResponseWithCaps)
async def update_beer_endpoint(beer_id: int, update_data: BeerUpdateSchema):
    async with GLOBAL_ASYNC_SESSION_MAKER() as session:
        updated_beer = await update_beer(session, beer_id, update_data, load_caps=True)

    if not updated_beer:
        raise HTTPException(status_code=404, detail="Beer not found")

    caps = [BeerCapShortResponse(id=cap.id, variant_name=cap.variant_name) for cap in updated_beer.caps]

    return BeerResponseWithCaps(id=updated_beer.id, name=updated_beer.name, caps=caps)
