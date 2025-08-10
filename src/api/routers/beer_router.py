import io
import logging
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.constants.responses import INTERNAL_SERVER_ERROR_RESPONSE, NOT_FOUND_RESPONSE
from src.api.dependencies.db import get_db_session
from src.api.dependencies.facades import get_beer_cap_facade
from src.api.schemas.beer.beer_create import BeerCreateSchema
from src.api.schemas.beer.beer_response import BeerResponseWithCaps
from src.api.schemas.beer.beer_update import BeerUpdateSchema
from src.api.schemas.beer_cap.beer_cap_create import BeerCapCreateSchema
from src.api.schemas.beer_cap.beer_cap_response import BeerCapResponseWithUrl
from src.api.schemas.beer_cap.beer_cap_response_base import BeerCapResponseBase
from src.api.schemas.common.status_response import StatusResponse
from src.api.schemas.country.country_response_base import CountryResponseBase
from src.db.crud.beer_crud import create_beer, get_all_beers, get_beer_by_id, update_beer
from src.services.beer_cap_facade import BeerCapFacade

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/beers", tags=["Beers"])


@router.post(
    "/",
    response_model=BeerResponseWithCaps,
    responses={422: {"description": "Validation Error"}, **INTERNAL_SERVER_ERROR_RESPONSE},
)
async def create_beer_endpoint(
    beer_data: BeerCreateSchema,
    db: AsyncSession = Depends(get_db_session),
) -> BeerResponseWithCaps:
    """Create a new beer."""
    new_beer = await create_beer(
        session=db,
        name=beer_data.name,
        beer_brand_id=beer_data.beer_brand_id,
        rating=beer_data.rating,
        country_id=beer_data.country_id,
    )

    return BeerResponseWithCaps(
        id=new_beer.id,
        name=new_beer.name,
        rating=new_beer.rating,
        caps=[],
        country=None,
    )


@router.get(
    "/",
    response_model=List[BeerResponseWithCaps],
    responses=INTERNAL_SERVER_ERROR_RESPONSE,
)
async def get_all_beers_endpoint(
    include_caps: bool = Query(False, description="Include caps for each beer"),
    include_country: bool = Query(False, description="Include country for each beer"),
    db: AsyncSession = Depends(get_db_session),
) -> List[BeerResponseWithCaps]:
    """Get all beers, optionally including their caps and country."""
    beers = await get_all_beers(db, load_caps=include_caps, load_country=include_country)

    return [
        BeerResponseWithCaps(
            id=beer.id,
            name=beer.name,
            rating=beer.rating,
            caps=(
                [
                    BeerCapResponseBase(id=cap.id, variant_name=cap.variant_name, collected_date=cap.collected_date)
                    for cap in beer.caps
                ]
                if include_caps
                else None
            ),
            country=(
                CountryResponseBase(
                    id=beer.country.id,
                    name=beer.country.name,
                    description=beer.country.description,
                )
                if include_country and beer.country
                else None
            ),
        )
        for beer in beers
    ]


@router.get(
    "/{beer_id}/",
    response_model=BeerResponseWithCaps,
    responses={**NOT_FOUND_RESPONSE, **INTERNAL_SERVER_ERROR_RESPONSE},
)
async def get_beer_by_id_endpoint(
    beer_id: int,
    include_caps: bool = Query(False, description="Include caps for the beer"),
    include_country: bool = Query(False, description="Include country for the beer"),
    db: AsyncSession = Depends(get_db_session),
) -> BeerResponseWithCaps:
    """Get a specific beer by its ID, optionally including its caps and country."""
    beer = await get_beer_by_id(db, beer_id, load_caps=include_caps, load_country=include_country)

    if not beer:
        raise HTTPException(status_code=404, detail="Beer not found.")

    caps = (
        [
            BeerCapResponseBase(id=cap.id, variant_name=cap.variant_name, collected_date=cap.collected_date)
            for cap in beer.caps
        ]
        if include_caps
        else None
    )
    country = (
        CountryResponseBase(
            id=beer.country.id,
            name=beer.country.name,
            description=beer.country.description,
        )
        if include_country and beer.country
        else None
    )

    return BeerResponseWithCaps(id=beer.id, name=beer.name, rating=beer.rating, caps=caps, country=country)


@router.delete(
    "/{beer_id}/",
    response_model=StatusResponse,
    responses={**NOT_FOUND_RESPONSE, **INTERNAL_SERVER_ERROR_RESPONSE},
)
async def delete_beer(
    beer_id: int,
    beer_cap_facade: BeerCapFacade = Depends(get_beer_cap_facade),
) -> StatusResponse:
    """
    Delete a beer by its ID.
    """
    deleted = await beer_cap_facade.delete_beer_and_caps(beer_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Beer not found.")

    logger.info("Deleted beer %s and its associated caps", beer_id)

    return StatusResponse(success=True, message="Beer deleted successfully.")


@router.patch(
    "/{beer_id}/",
    response_model=BeerResponseWithCaps,
    responses={
        **NOT_FOUND_RESPONSE,
        422: {"description": "Validation Error"},
        **INTERNAL_SERVER_ERROR_RESPONSE,
    },
)
async def update_beer_endpoint(
    beer_id: int,
    update_data: BeerUpdateSchema,
    db: AsyncSession = Depends(get_db_session),
) -> BeerResponseWithCaps:
    """
    Update beer details.
    """
    updated_beer = await update_beer(db, beer_id, update_data, load_caps=True, load_country=True)

    if not updated_beer:
        raise HTTPException(status_code=404, detail="Beer not found.")

    logger.info("Updated beer %s with data: %s", beer_id, update_data.dict())

    caps = [
        BeerCapResponseBase(id=cap.id, variant_name=cap.variant_name, collected_date=cap.collected_date)
        for cap in updated_beer.caps
    ]
    country = (
        CountryResponseBase(
            id=updated_beer.country.id,
            name=updated_beer.country.name,
            description=updated_beer.country.description,
        )
        if updated_beer.country
        else None
    )

    return BeerResponseWithCaps(
        id=updated_beer.id, name=updated_beer.name, rating=updated_beer.rating, caps=caps, country=country
    )
