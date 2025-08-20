import logging

from fastapi import APIRouter, Depends, Form, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.constants.responses import (
    INTERNAL_SERVER_ERROR_RESPONSE,
    NOT_FOUND_RESPONSE,
)
from src.api.dependencies.db import get_db_session
from src.api.schemas.beer.beer_response_base import BeerResponseBase
from src.api.schemas.country.country_create import CountryCreateSchema
from src.api.schemas.country.country_response import CountryResponseWithBeers
from src.api.schemas.country.country_response_base import CountryResponseBase
from src.api.schemas.country.country_update import CountryUpdateSchema
from src.db.crud.country_crud import (
    create_country,
    delete_country,
    get_all_countries,
    get_country_by_id,
    update_country,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/countries", tags=["Countries"])


@router.post(
    "/",
    response_model=CountryResponseWithBeers,
    responses=INTERNAL_SERVER_ERROR_RESPONSE,
)
async def create_country_endpoint(
    name: str = Form(..., description="Name of the country"),
    description: str = Form(..., description="Description of the country"),
    db: AsyncSession = Depends(get_db_session),
) -> CountryResponseWithBeers:
    country = await create_country(
        db, CountryCreateSchema(name=name, description=description)
    )
    return CountryResponseWithBeers(
        id=country.id,
        name=country.name,
        description=country.description,
        beers=[],
    )


@router.get(
    "/",
    response_model=list[CountryResponseWithBeers],
    responses=INTERNAL_SERVER_ERROR_RESPONSE,
)
async def get_all_countries_endpoint(
    include_beers: bool = Query(False, description="Include beers for each country"),
    db: AsyncSession = Depends(get_db_session),
) -> list[CountryResponseWithBeers]:
    countries = await get_all_countries(db, load_beers=include_beers)
    return [
        CountryResponseWithBeers(
            id=country.id,
            name=country.name,
            description=country.description,
            beers=(
                [
                    BeerResponseBase(id=beer.id, name=beer.name, rating=beer.rating)
                    for beer in country.beers
                ]
                if include_beers
                else None
            ),
        )
        for country in countries
    ]


@router.get(
    "/{country_id}/",
    response_model=CountryResponseWithBeers,
    responses={**NOT_FOUND_RESPONSE, **INTERNAL_SERVER_ERROR_RESPONSE},
)
async def get_country_by_id_endpoint(
    country_id: int,
    include_beers: bool = Query(False, description="Include beers for the country"),
    db: AsyncSession = Depends(get_db_session),
) -> CountryResponseWithBeers:
    country = await get_country_by_id(db, country_id, load_beers=include_beers)
    if not country:
        raise HTTPException(status_code=404, detail="Country not found.")

    beers = (
        [
            BeerResponseBase(id=beer.id, name=beer.name, rating=beer.rating)
            for beer in country.beers
        ]
        if include_beers
        else None
    )
    return CountryResponseWithBeers(
        id=country.id, name=country.name, description=country.description, beers=beers
    )


@router.delete(
    "/{country_id}/",
    response_model=CountryResponseBase,
    responses={**NOT_FOUND_RESPONSE, **INTERNAL_SERVER_ERROR_RESPONSE},
)
async def delete_country_endpoint(
    country_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> CountryResponseBase:
    country = await get_country_by_id(db, country_id)
    if not country:
        raise HTTPException(status_code=404, detail="Country not found.")
    await delete_country(db, country_id)
    return CountryResponseBase(
        id=country.id, name=country.name, description=country.description
    )


@router.patch(
    "/{country_id}/",
    response_model=CountryResponseWithBeers,
    responses={**NOT_FOUND_RESPONSE, **INTERNAL_SERVER_ERROR_RESPONSE},
)
async def update_country_endpoint(
    country_id: int,
    update_data: CountryUpdateSchema,
    db: AsyncSession = Depends(get_db_session),
) -> CountryResponseWithBeers:
    updated_country = await update_country(db, country_id, update_data, load_beers=True)
    if not updated_country:
        raise HTTPException(status_code=404, detail="Country not found.")
    return CountryResponseWithBeers(
        id=updated_country.id,
        name=updated_country.name,
        description=updated_country.description,
        beers=[
            BeerResponseBase(id=beer.id, name=beer.name, rating=beer.rating)
            for beer in updated_country.beers
        ],
    )
