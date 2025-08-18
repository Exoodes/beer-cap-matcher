import logging
from typing import List

from fastapi import APIRouter, Depends, Form, HTTPException, Query
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
from src.api.schemas.common.status_response import StatusResponse
from src.db.crud.beer_brand_crud import (
    create_beer_brand,
    delete_beer_brand,
    get_all_beer_brands,
    get_beer_brand_by_id,
    update_beer_brand,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/beer_brands", tags=["Beer Brands"])


@router.post(
    "/",
    response_model=BeerBrandResponseWithBeers,
    responses={
        422: {"description": "Validation Error"},
        **INTERNAL_SERVER_ERROR_RESPONSE,
    },
)
async def create_beer_brand_endpoint(
    name: str = Form(..., description="Name of the beer brand"),
    db: AsyncSession = Depends(get_db_session),
) -> BeerBrandResponseWithBeers:
    data = BeerBrandCreateSchema(name=name)

    beer_brand = await create_beer_brand(db, name=data.name)
    logger.info("Created beer_brand %s", data.name)
    return BeerBrandResponseWithBeers(id=beer_brand.id, name=beer_brand.name, beers=[])


@router.get(
    "/",
    response_model=List[BeerBrandResponseWithBeers],
    responses=INTERNAL_SERVER_ERROR_RESPONSE,
)
async def get_all_beer_brands_endpoint(
    include_beers: bool = Query(False, description="Include beers for each beer_brand"),
    db: AsyncSession = Depends(get_db_session),
) -> List[BeerBrandResponseWithBeers]:
    beer_brands = await get_all_beer_brands(db, load_beers=include_beers)
    return [
        BeerBrandResponseWithBeers(
            id=b.id,
            name=b.name,
            beers=(
                [BeerResponseBase(id=beer.id, name=beer.name) for beer in b.beers]
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
        [BeerResponseBase(id=beer.id, name=beer.name) for beer in beer_brand.beers]
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
    response_model=StatusResponse,
    responses={**NOT_FOUND_RESPONSE, **INTERNAL_SERVER_ERROR_RESPONSE},
)
async def delete_beer_brand_endpoint(
    beer_brand_id: int, db: AsyncSession = Depends(get_db_session)
) -> StatusResponse:
    deleted = await delete_beer_brand(db, beer_brand_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="beer_brand not found.")
    logger.info("Deleted beer_brand %s", beer_brand_id)
    return StatusResponse(success=True, message="beer_brand deleted successfully.")


@router.patch(
    "/{beer_brand_id}/",
    response_model=BeerBrandResponseWithBeers,
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
    beers = [BeerResponseBase(id=beer.id, name=beer.name) for beer in beer_brand.beers]
    return BeerBrandResponseWithBeers(
        id=beer_brand.id,
        name=beer_brand.name,
        beers=beers,
    )
