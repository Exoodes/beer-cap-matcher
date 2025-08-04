import io
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.constants.responses import INTERNAL_SERVER_ERROR_RESPONSE, NOT_FOUND_RESPONSE
from src.api.dependencies.db import get_db_session
from src.api.dependencies.facades import get_beer_cap_facade
from src.api.schemas.beer.beer_response import BeerResponseWithCaps
from src.api.schemas.beer.beer_response_base import BeerResponseBase
from src.api.schemas.beer.beer_update import BeerUpdateSchema
from src.api.schemas.beer_cap.beer_cap_create import BeerCapCreateSchema
from src.api.schemas.beer_cap.beer_cap_response import BeerCapResponseWithUrl
from src.api.schemas.beer_cap.beer_cap_response_base import BeerCapResponseBase
from src.api.schemas.common.status_response import StatusResponse
from src.db.crud.beer_crud import get_all_beers, get_beer_by_id, update_beer
from src.services.beer_cap_facade import BeerCapFacade

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/beers", tags=["Beers"])


@router.get(
    "/",
    response_model=List[BeerResponseWithCaps],
    responses=INTERNAL_SERVER_ERROR_RESPONSE,
)
async def get_all_beers_endpoint(
    include_caps: bool = Query(False, description="Include caps for each beer"),
    db: AsyncSession = Depends(get_db_session),
) -> List[BeerResponseWithCaps]:
    """
    Get all beers, optionally including their caps.
    """
    beers = await get_all_beers(db, load_caps=include_caps)

    return [
        BeerResponseWithCaps(
            id=beer.id,
            name=beer.name,
            caps=[BeerCapResponseBase(id=cap.id, variant_name=cap.variant_name) for cap in beer.caps]
            if include_caps else None
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
    db: AsyncSession = Depends(get_db_session),
) -> BeerResponseWithCaps:
    """
    Get a specific beer by its ID, optionally including its caps.
    """
    beer = await get_beer_by_id(db, beer_id, load_caps=include_caps)

    if not beer:
        raise HTTPException(status_code=404, detail="Beer not found.")

    caps = (
        [BeerCapResponseBase(id=cap.id, variant_name=cap.variant_name) for cap in beer.caps]
        if include_caps else None
    )

    return BeerResponseWithCaps(id=beer.id, name=beer.name, caps=caps)


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
    updated_beer = await update_beer(db, beer_id, update_data, load_caps=True)

    if not updated_beer:
        raise HTTPException(status_code=404, detail="Beer not found.")

    logger.info("Updated beer %s with data: %s", beer_id, update_data.dict())

    caps = [
        BeerCapResponseBase(id=cap.id, variant_name=cap.variant_name)
        for cap in updated_beer.caps
    ]

    return BeerResponseWithCaps(id=updated_beer.id, name=updated_beer.name, caps=caps)


@router.post(
    "/{beer_id}/caps/",
    response_model=BeerCapResponseWithUrl,
    responses={
        **NOT_FOUND_RESPONSE,
        422: {"description": "Validation Error"},
        **INTERNAL_SERVER_ERROR_RESPONSE,
    },
)
async def create_cap_for_existing_beer(
    beer_id: int,
    variant_name: Optional[str] = Form(None, max_length=100),
    file: UploadFile = File(...),
    beer_cap_facade: BeerCapFacade = Depends(get_beer_cap_facade),
) -> BeerCapResponseWithUrl:
    """
    Upload a beer cap image for an existing beer.
    """
    contents = await file.read()

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are allowed.")

    file_like = io.BytesIO(contents)
    cap_metadata = BeerCapCreateSchema(filename=file.filename, variant_name=variant_name)

    beer_cap = await beer_cap_facade.create_cap_for_existing_beer_and_upload(
        beer_id, cap_metadata, file_like, len(contents), file.content_type
    )

    if not beer_cap:
        raise HTTPException(status_code=404, detail="Beer not found.")

    logger.info("Uploaded new cap for beer %s, filename: %s", beer_id, file.filename)

    url = beer_cap_facade.get_presigned_url_for_cap(beer_cap.s3_key)
    beer_response = BeerResponseBase(id=beer_cap.beer_id, name=beer_cap.beer.name)

    return BeerCapResponseWithUrl(
        id=beer_cap.id,
        variant_name=beer_cap.variant_name,
        presigned_url=url,
        beer=beer_response,
    )
