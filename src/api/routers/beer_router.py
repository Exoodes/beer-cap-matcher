import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.constants.responses import (
    INTERNAL_SERVER_ERROR_RESPONSE,
    NOT_FOUND_RESPONSE,
)
from src.api.dependencies.db import get_db_session
from src.api.dependencies.facades import get_beer_cap_facade
from src.api.schemas.beer.beer_create import BeerCreateSchema
from src.api.schemas.beer.beer_response import BeerResponseWithCaps
from src.api.schemas.beer.beer_update import BeerUpdateSchema
from src.api.schemas.beer_brand.beer_brand_response_base import BeerBrandResponseBase
from src.api.schemas.beer_cap.beer_cap_response_base import BeerCapResponseBase
from src.api.schemas.common.merge import MergeSchema
from src.api.schemas.country.country_response_base import CountryResponseBase
from src.db.crud.beer_crud import (
    count_caps_by_beer,
    create_beer,
    get_all_beers,
    get_beer_by_id,
    update_beer,
)
from src.db.crud.merge_crud import merge_beers
from src.services.beer_cap_facade import BeerCapFacade
from src.api.dependencies.auth import verify_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/beers", tags=["Beers"])


@router.post(
    "/",
    response_model=BeerResponseWithCaps,
    status_code=201,
    dependencies=[Depends(verify_admin)],
    responses={
        422: {"description": "Validation Error"},
        **INTERNAL_SERVER_ERROR_RESPONSE,
    },
)
async def create_beer_endpoint(
    beer_data: BeerCreateSchema,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> BeerResponseWithCaps:
    new_beer = await create_beer(
        session=db,
        name=beer_data.name,
        beer_brand_id=beer_data.beer_brand_id,
        rating=beer_data.rating if beer_data.rating is not None else 0,
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
    response_model=list[BeerResponseWithCaps],
    responses=INTERNAL_SERVER_ERROR_RESPONSE,
)
async def get_all_beers_endpoint(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    include_caps: bool = Query(False, description="Include caps for each beer"),
    include_country: bool = Query(False, description="Include country for each beer"),
    include_beer_brand: bool = Query(
        False, description="Include beer brand for each beer"
    ),
) -> list[BeerResponseWithCaps]:
    beers = await get_all_beers(
        db,
        load_caps=include_caps,
        load_country=include_country,
        load_beer_brand=include_beer_brand,
    )
    cap_counts = await count_caps_by_beer(db)

    return [
        BeerResponseWithCaps(
            id=beer.id,
            name=beer.name,
            rating=beer.rating,
            beer_brand=(
                BeerBrandResponseBase.model_validate(beer.beer_brand)
                if include_beer_brand and beer.beer_brand
                else None
            ),
            caps=(
                [
                    BeerCapResponseBase(
                        id=cap.id,
                        variant_name=cap.variant_name,
                        collected_date=cap.collected_date,
                    )
                    for cap in beer.caps
                ]
                if include_caps
                else None
            ),
            cap_count=cap_counts.get(beer.id, 0),
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
    db: Annotated[AsyncSession, Depends(get_db_session)],
    include_caps: bool = Query(False, description="Include caps for the beer"),
    include_country: bool = Query(False, description="Include country for the beer"),
) -> BeerResponseWithCaps:
    beer = await get_beer_by_id(
        db, beer_id, load_caps=include_caps, load_country=include_country
    )

    if not beer:
        raise HTTPException(status_code=404, detail="Beer not found.")

    caps = (
        [
            BeerCapResponseBase(
                id=cap.id,
                variant_name=cap.variant_name,
                collected_date=cap.collected_date,
            )
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

    return BeerResponseWithCaps(
        id=beer.id, name=beer.name, rating=beer.rating, caps=caps, country=country
    )


@router.delete(
    "/{beer_id}/",
    status_code=204,
    dependencies=[Depends(verify_admin)],
    responses={**NOT_FOUND_RESPONSE, **INTERNAL_SERVER_ERROR_RESPONSE},
)
async def delete_beer(
    beer_id: int,
    beer_cap_facade: Annotated[BeerCapFacade, Depends(get_beer_cap_facade)],
) -> None:
    deleted = await beer_cap_facade.delete_beer_and_caps(beer_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Beer not found.")

    logger.info("Deleted beer %s and its associated caps", beer_id)


@router.patch(
    "/{beer_id}/",
    response_model=BeerResponseWithCaps,
    dependencies=[Depends(verify_admin)],
    responses={
        **NOT_FOUND_RESPONSE,
        422: {"description": "Validation Error"},
        **INTERNAL_SERVER_ERROR_RESPONSE,
    },
)
async def update_beer_endpoint(
    beer_id: int,
    update_data: BeerUpdateSchema,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> BeerResponseWithCaps:
    updated_beer = await update_beer(
        db, beer_id, update_data, load_caps=True, load_country=True
    )

    if not updated_beer:
        raise HTTPException(status_code=404, detail="Beer not found.")

    logger.info("Updated beer %s with data: %s", beer_id, update_data.model_dump())

    caps = [
        BeerCapResponseBase(
            id=cap.id, variant_name=cap.variant_name, collected_date=cap.collected_date
        )
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
        id=updated_beer.id,
        name=updated_beer.name,
        rating=updated_beer.rating,
        caps=caps,
        country=country,
    )


@router.post(
    "/{beer_id}/merge/",
    response_model=BeerResponseWithCaps,
    dependencies=[Depends(verify_admin)],
    responses={
        **NOT_FOUND_RESPONSE,
        422: {"description": "Validation Error"},
        **INTERNAL_SERVER_ERROR_RESPONSE,
    },
)
async def merge_beer_endpoint(
    beer_id: int,
    data: MergeSchema,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> BeerResponseWithCaps:
    """
    Merge a duplicate beer into another: its caps move to `into_id` and the
    beer is deleted. A country or rating the target lacks is taken over.
    """
    if beer_id == data.into_id:
        raise HTTPException(
            status_code=422, detail="A beer can't be merged into itself."
        )

    if not await merge_beers(db, beer_id, data.into_id):
        raise HTTPException(status_code=404, detail="Beer not found.")
    logger.info("Merged beer %s into beer %s", beer_id, data.into_id)

    beer = await get_beer_by_id(
        db, data.into_id, load_caps=True, load_beer_brand=True, load_country=True
    )
    assert beer
    return BeerResponseWithCaps(
        id=beer.id,
        name=beer.name,
        rating=beer.rating,
        beer_brand=BeerBrandResponseBase.model_validate(beer.beer_brand),
        country=(
            CountryResponseBase.model_validate(beer.country) if beer.country else None
        ),
        caps=[
            BeerCapResponseBase(
                id=cap.id,
                variant_name=cap.variant_name,
                collected_date=cap.collected_date,
            )
            for cap in beer.caps
        ],
        cap_count=len(beer.caps),
    )
