import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.constants.responses import (
    INTERNAL_SERVER_ERROR_RESPONSE,
    NOT_FOUND_RESPONSE,
)
from src.api.dependencies.db import get_db_session
from src.api.schemas.beer.beer_response_base import BeerResponseBase
from src.api.schemas.common.merge import MergeSchema
from src.api.schemas.country.country_create import CountryCreateSchema
from src.api.schemas.country.country_response import CountryResponseWithBeers
from src.api.schemas.country.country_update import CountryUpdateSchema
from src.db.crud.country_crud import (
    count_beers_by_country,
    create_country,
    delete_country,
    get_all_countries,
    get_country_by_id,
    update_country,
)
from src.db.crud.merge_crud import merge_countries
from src.api.dependencies.auth import verify_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/countries", tags=["Countries"])


@router.post(
    "/",
    response_model=CountryResponseWithBeers,
    status_code=201,
    dependencies=[Depends(verify_admin)],
    responses=INTERNAL_SERVER_ERROR_RESPONSE,
)
async def create_country_endpoint(
    data: CountryCreateSchema,
    db: AsyncSession = Depends(get_db_session),
) -> CountryResponseWithBeers:
    country = await create_country(db, data)
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
    beer_counts = await count_beers_by_country(db)
    return [
        CountryResponseWithBeers(
            id=country.id,
            name=country.name,
            description=country.description,
            beer_count=beer_counts.get(country.id, 0),
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
    status_code=204,
    dependencies=[Depends(verify_admin)],
    responses={**NOT_FOUND_RESPONSE, **INTERNAL_SERVER_ERROR_RESPONSE},
)
async def delete_country_endpoint(
    country_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> None:
    country = await get_country_by_id(db, country_id)
    if not country:
        raise HTTPException(status_code=404, detail="Country not found.")
    await delete_country(db, country_id)


@router.patch(
    "/{country_id}/",
    response_model=CountryResponseWithBeers,
    dependencies=[Depends(verify_admin)],
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


@router.post(
    "/{country_id}/merge/",
    response_model=CountryResponseWithBeers,
    dependencies=[Depends(verify_admin)],
    responses={
        **NOT_FOUND_RESPONSE,
        422: {"description": "Validation Error"},
        **INTERNAL_SERVER_ERROR_RESPONSE,
    },
)
async def merge_country_endpoint(
    country_id: int,
    data: MergeSchema,
    db: AsyncSession = Depends(get_db_session),
) -> CountryResponseWithBeers:
    """
    Merge a duplicate country into another: its beers move to `into_id` and
    the country is deleted.
    """
    if country_id == data.into_id:
        raise HTTPException(
            status_code=422, detail="A country can't be merged into itself."
        )

    if not await merge_countries(db, country_id, data.into_id):
        raise HTTPException(status_code=404, detail="Country not found.")
    logger.info("Merged country %s into %s", country_id, data.into_id)

    country = await get_country_by_id(db, data.into_id, load_beers=True)
    assert country
    return CountryResponseWithBeers(
        id=country.id,
        name=country.name,
        description=country.description,
        beers=[
            BeerResponseBase(id=beer.id, name=beer.name, rating=beer.rating)
            for beer in country.beers
        ],
        beer_count=len(country.beers),
    )
