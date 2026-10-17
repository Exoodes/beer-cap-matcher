import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.constants.responses import (
    INTERNAL_SERVER_ERROR_RESPONSE,
    NOT_FOUND_RESPONSE,
)
from src.api.dependencies.db import get_db_session
from src.api.schemas.beer.beer_response_base import BeerResponseBase
from src.api.schemas.beer_brand.beer_brand_create import BeerBrandCreateSchema
from src.api.schemas.beer_brand.beer_brand_response import BeerBrandResponseWithBeers
from src.api.schemas.beer_brand.beer_brand_update import BeerBrandUpdateSchema
from src.api.schemas.common.merge import MergeSchema
from src.db.crud.beer_brand_crud import (
    count_beers_by_brand,
    create_beer_brand,
    delete_beer_brand,
    get_all_beer_brands,
    get_beer_brand_by_id,
    update_beer_brand,
)
from src.db.crud.merge_crud import merge_beer_brands
from src.api.dependencies.auth import verify_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/beer_brands", tags=["Beer Brands"])


@router.post(
    "/",
    response_model=BeerBrandResponseWithBeers,
    status_code=201,
    dependencies=[Depends(verify_admin)],
    responses={
        422: {"description": "Validation Error"},
        **INTERNAL_SERVER_ERROR_RESPONSE,
    },
)
async def create_beer_brand_endpoint(
    data: BeerBrandCreateSchema,
    db: AsyncSession = Depends(get_db_session),
) -> BeerBrandResponseWithBeers:
    beer_brand = await create_beer_brand(db, name=data.name)
    logger.info("Created beer_brand %s", data.name)
    return BeerBrandResponseWithBeers(id=beer_brand.id, name=beer_brand.name, beers=[])


@router.get(
    "/",
    response_model=list[BeerBrandResponseWithBeers],
    responses=INTERNAL_SERVER_ERROR_RESPONSE,
)
async def get_all_beer_brands_endpoint(
    include_beers: bool = Query(False, description="Include beers for each beer_brand"),
    db: AsyncSession = Depends(get_db_session),
) -> list[BeerBrandResponseWithBeers]:
    beer_brands = await get_all_beer_brands(db, load_beers=include_beers)
    beer_counts = await count_beers_by_brand(db)
    return [
        BeerBrandResponseWithBeers(
            id=b.id,
            name=b.name,
            beer_count=beer_counts.get(b.id, 0),
            beers=(
                [
                    BeerResponseBase(id=beer.id, name=beer.name, rating=beer.rating)
                    for beer in b.beers
                ]
                if include_beers
                else None
            ),
        )
        for b in beer_brands
    ]


@router.get(
    "/{beer_brand_id}/",
    response_model=BeerBrandResponseWithBeers,
    responses={**NOT_FOUND_RESPONSE, **INTERNAL_SERVER_ERROR_RESPONSE},
)
async def get_beer_brand_by_id_endpoint(
    beer_brand_id: int,
    include_beers: bool = Query(False, description="Include beers for this beer_brand"),
    db: AsyncSession = Depends(get_db_session),
) -> BeerBrandResponseWithBeers:
    beer_brand = await get_beer_brand_by_id(db, beer_brand_id, load_beers=include_beers)
    if not beer_brand:
        raise HTTPException(status_code=404, detail="beer_brand not found.")

    beers = (
        [
            BeerResponseBase(id=beer.id, name=beer.name, rating=beer.rating)
            for beer in beer_brand.beers
        ]
        if include_beers
        else None
    )
    return BeerBrandResponseWithBeers(
        id=beer_brand.id,
        name=beer_brand.name,
        beers=beers,
    )


@router.delete(
    "/{beer_brand_id}/",
    status_code=204,
    dependencies=[Depends(verify_admin)],
    responses={**NOT_FOUND_RESPONSE, **INTERNAL_SERVER_ERROR_RESPONSE},
)
async def delete_beer_brand_endpoint(
    beer_brand_id: int, db: AsyncSession = Depends(get_db_session)
) -> None:
    deleted = await delete_beer_brand(db, beer_brand_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="beer_brand not found.")
    logger.info("Deleted beer_brand %s", beer_brand_id)


@router.patch(
    "/{beer_brand_id}/",
    response_model=BeerBrandResponseWithBeers,
    dependencies=[Depends(verify_admin)],
    responses={
        422: {"description": "Validation Error"},
        **NOT_FOUND_RESPONSE,
        **INTERNAL_SERVER_ERROR_RESPONSE,
    },
)
async def update_beer_brand_endpoint(
    beer_brand_id: int,
    update_data: BeerBrandUpdateSchema,
    db: AsyncSession = Depends(get_db_session),
) -> BeerBrandResponseWithBeers:
    beer_brand = await update_beer_brand(
        db, beer_brand_id, update_data, load_beers=True
    )
    if not beer_brand:
        raise HTTPException(status_code=404, detail="beer_brand not found.")
    logger.info(
        "Updated beer_brand %s with data: %s", beer_brand_id, update_data.model_dump()
    )
    beers = [
        BeerResponseBase(id=beer.id, name=beer.name, rating=beer.rating)
        for beer in beer_brand.beers
    ]
    return BeerBrandResponseWithBeers(
        id=beer_brand.id,
        name=beer_brand.name,
        beers=beers,
    )


@router.post(
    "/{beer_brand_id}/merge/",
    response_model=BeerBrandResponseWithBeers,
    dependencies=[Depends(verify_admin)],
    responses={
        **NOT_FOUND_RESPONSE,
        422: {"description": "Validation Error"},
        **INTERNAL_SERVER_ERROR_RESPONSE,
    },
)
async def merge_beer_brand_endpoint(
    beer_brand_id: int,
    data: MergeSchema,
    db: AsyncSession = Depends(get_db_session),
) -> BeerBrandResponseWithBeers:
    """
    Merge a duplicate brand into another: its beers move to `into_id` and the
    brand is deleted. A beer the target brand already has (same name, ignoring
    case) is merged into that beer.
    """
    if beer_brand_id == data.into_id:
        raise HTTPException(
            status_code=422, detail="A brand can't be merged into itself."
        )

    if not await merge_beer_brands(db, beer_brand_id, data.into_id):
        raise HTTPException(status_code=404, detail="beer_brand not found.")
    logger.info("Merged beer_brand %s into %s", beer_brand_id, data.into_id)

    beer_brand = await get_beer_brand_by_id(db, data.into_id, load_beers=True)
    assert beer_brand
    return BeerBrandResponseWithBeers(
        id=beer_brand.id,
        name=beer_brand.name,
        beers=[
            BeerResponseBase(id=beer.id, name=beer.name, rating=beer.rating)
            for beer in beer_brand.beers
        ],
        beer_count=len(beer_brand.beers),
    )
