# File: src/api/routers/beer_cap_router.py

import io
import logging
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.constants.responses import (
    INTERNAL_SERVER_ERROR_RESPONSE,
    NOT_FOUND_RESPONSE,
)
from src.api.dependencies.db import get_db_session
from src.api.dependencies.facades import get_beer_cap_facade
from src.api.schemas.beer_cap.beer_cap_create import BeerCapCreateSchema
from src.api.schemas.beer_cap.beer_cap_response import BeerCapResponseWithUrl
from src.api.schemas.beer_cap.beer_cap_update import BeerCapUpdateSchema
from src.api.schemas.common.status_response import StatusResponse
from src.api.utils import build_beer_cap_response
from src.db.crud.beer_cap_crud import (
    get_all_beer_caps,
    get_beer_cap_by_id,
    get_beer_caps_by_beer_id,
    update_beer_cap,
)
from src.services.beer_cap_facade import BeerCapFacade

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/beer_caps", tags=["Beer Caps"])


@router.post(
    "/",
    response_model=BeerCapResponseWithUrl,
    responses={
        404: {"description": "Beer not found"},
        422: {"description": "Validation Error"},
        **INTERNAL_SERVER_ERROR_RESPONSE,
    },
)
async def create_cap_endpoint(
    file: UploadFile = File(...),
    variant_name: Optional[str] = Form(None, max_length=100),
    collected_date: Optional[date] = Form(None),
    beer_id: Optional[int] = Form(None, ge=1),
    beer_name: Optional[str] = Form(None, min_length=1, max_length=100),
    beer_brand_id: Optional[int] = Form(None, ge=1),
    beer_brand_name: Optional[str] = Form(None, min_length=1, max_length=100),
    country_id: Optional[int] = Form(None, ge=1),
    country_name: Optional[str] = Form(None, min_length=1, max_length=100),
    beer_cap_facade: BeerCapFacade = Depends(get_beer_cap_facade),
) -> BeerCapResponseWithUrl:
    """
    Creates a new beer cap. Can optionally create a new beer, beer brand, and/or country.
    - If `beer_id` is provided, a new cap is added to that existing beer.
    - If `beer_name` is provided, a new beer is created. The beer brand and country
      will be linked by ID or created by name based on the provided values.
    """
    contents = await file.read()

    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400, detail="Invalid file type. Only images are allowed."
        )

    file_like = io.BytesIO(contents)

    cap_data = BeerCapCreateSchema(
        filename=file.filename,
        variant_name=variant_name,
        collected_date=collected_date,
        beer_id=beer_id,
        beer_name=beer_name,
        beer_brand_id=beer_brand_id,
        beer_brand_name=beer_brand_name,
        country_id=country_id,
        country_name=country_name,
    )

    beer_cap = await beer_cap_facade.create_cap_and_related_entities(
        cap_metadata=cap_data,
        image_data=file_like,
        image_length=len(contents),
        content_type=file.content_type,
    )

    if not beer_cap:
        raise HTTPException(status_code=404, detail="Beer not found.")

    logger.info(
        "Successfully created beer cap %s for beer %s", beer_cap.id, beer_cap.beer.name
    )

    return build_beer_cap_response(beer_cap, beer_cap_facade)


@router.get(
    "/",
    response_model=List[BeerCapResponseWithUrl],
    responses=INTERNAL_SERVER_ERROR_RESPONSE,
)
async def api_get_all_beer_caps(
    beer_cap_facade: BeerCapFacade = Depends(get_beer_cap_facade),
    db: AsyncSession = Depends(get_db_session),
) -> List[BeerCapResponseWithUrl]:
    """
    Retrieve all beer caps with their presigned URLs.
    """
    beer_caps = await get_all_beer_caps(db, load_beer=True)

    return [build_beer_cap_response(cap, beer_cap_facade) for cap in beer_caps]


@router.get(
    "/by-beer/{beer_id}/",
    response_model=List[BeerCapResponseWithUrl],
    responses={**NOT_FOUND_RESPONSE, **INTERNAL_SERVER_ERROR_RESPONSE},
)
async def get_all_caps_from_beer(
    beer_id: int,
    beer_cap_facade: BeerCapFacade = Depends(get_beer_cap_facade),
    db: AsyncSession = Depends(get_db_session),
) -> List[BeerCapResponseWithUrl]:
    """
    Retrieve all beer caps for a specific beer ID.
    """
    beer_caps = await get_beer_caps_by_beer_id(db, beer_id, load_beer=True)

    if not beer_caps:
        raise HTTPException(status_code=404, detail="No beer caps found for this beer.")

    return [build_beer_cap_response(cap, beer_cap_facade) for cap in beer_caps]


@router.get(
    "/{beer_cap_id}/",
    response_model=BeerCapResponseWithUrl,
    responses={**NOT_FOUND_RESPONSE, **INTERNAL_SERVER_ERROR_RESPONSE},
)
async def get_beer_cap(
    beer_cap_id: int,
    beer_cap_facade: BeerCapFacade = Depends(get_beer_cap_facade),
    db: AsyncSession = Depends(get_db_session),
) -> BeerCapResponseWithUrl:
    """
    Get a beer cap by ID, including its presigned URL.
    """
    beer_cap = await get_beer_cap_by_id(db, beer_cap_id, load_beer=True)

    if not beer_cap:
        raise HTTPException(status_code=404, detail="Beer cap not found.")

    return build_beer_cap_response(beer_cap, beer_cap_facade)


@router.delete(
    "/{beer_cap_id}/",
    response_model=StatusResponse,
    responses={**NOT_FOUND_RESPONSE, **INTERNAL_SERVER_ERROR_RESPONSE},
)
async def delete_beer_cap(
    beer_cap_id: int,
    beer_cap_facade: BeerCapFacade = Depends(get_beer_cap_facade),
) -> StatusResponse:
    """
    Delete a beer cap and its augmented caps.
    """
    success = await beer_cap_facade.delete_beer_cap_and_its_augmented_caps(beer_cap_id)

    if not success:
        raise HTTPException(status_code=404, detail="Beer cap not found.")

    logger.info("Deleted beer cap %s and its augmented caps.", beer_cap_id)

    return StatusResponse(
        success=True,
        message="Beer cap and its augmented caps deleted successfully.",
    )


@router.patch(
    "/{beer_cap_id}/",
    response_model=BeerCapResponseWithUrl,
    responses={
        **NOT_FOUND_RESPONSE,
        422: {"description": "Validation Error"},
        **INTERNAL_SERVER_ERROR_RESPONSE,
    },
)
async def update_beer_cap_endpoint(
    beer_cap_id: int,
    update_data: BeerCapUpdateSchema,
    beer_cap_facade: BeerCapFacade = Depends(get_beer_cap_facade),
    db: AsyncSession = Depends(get_db_session),
) -> BeerCapResponseWithUrl:
    """
    Update beer cap details.
    """
    updated_cap = await update_beer_cap(db, beer_cap_id, update_data, load_beer=True)

    if not updated_cap:
        raise HTTPException(status_code=404, detail="Beer cap not found.")

    logger.info("Updated beer cap %s with data: %s", beer_cap_id, update_data.dict())

    return build_beer_cap_response(updated_cap, beer_cap_facade)
