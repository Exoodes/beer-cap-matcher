import io
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.params import Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.beer.beer_response import BeerCapShortResponse, BeerResponseWithCaps
from src.api.schemas.beer.update_schema import BeerUpdateSchema
from src.api.schemas.beer_cap.beer_cap_response import BeerCapResponse, BeerResponse
from src.api.schemas.common.delete_status_response import DeleteStatusResponse
from src.db.crud.beer import get_all_beers, get_beer_by_id, update_beer
from src.db.database import GLOBAL_ASYNC_SESSION_MAKER
from src.dependencies.db import get_db_session
from src.dependencies.facades import get_beer_cap_facade
from src.facades.beer_cap_facade import BeerCapFacade
from src.schemas.beer_cap_schema import BeerCapCreateSchema
from src.storage.minio_client import MinioClientWrapper

router = APIRouter(prefix="/beers", tags=["Beers"])


@router.get("/caps", response_model=list[BeerResponseWithCaps])
async def get_all_beer_caps(
    include_caps: bool = Query(False, description="Include caps for each beer"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get all beer caps with their associated beers.
    """
    beers = await get_all_beers(db, load_caps=include_caps)

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
async def api_get_beer_by_id(
    beer_id: int,
    include_caps: bool = Query(False, description="Include caps for the beer"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get a specific beer by its ID, optionally including its caps.
    """
    beer = await get_beer_by_id(db, beer_id, load_caps=include_caps)

    if not beer:
        raise HTTPException(status_code=404, detail="Beer not found.")

    if include_caps:
        caps = [BeerCapShortResponse(id=cap.id, variant_name=cap.variant_name) for cap in beer.caps]
    else:
        caps = None

    return BeerResponseWithCaps(id=beer.id, name=beer.name, caps=caps)


@router.delete("/{beer_id}", response_model=DeleteStatusResponse)
async def api_delete_beer(beer_id: int, beer_cap_facade: BeerCapFacade = Depends(get_beer_cap_facade)):
    """
    Delete a beer by its ID.
    """
    deleted = await beer_cap_facade.delete_beer_and_caps(beer_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Beer not found.")

    return DeleteStatusResponse(success=True, message="Beer deleted successfully.")


@router.patch("/{beer_id}", response_model=BeerResponseWithCaps)
async def update_beer_endpoint(beer_id: int, update_data: BeerUpdateSchema, db: AsyncSession = Depends(get_db_session)):
    updated_beer = await update_beer(db, beer_id, update_data, load_caps=True)

    if not updated_beer:
        raise HTTPException(status_code=404, detail="Beer not found")

    caps = [BeerCapShortResponse(id=cap.id, variant_name=cap.variant_name) for cap in updated_beer.caps]

    return BeerResponseWithCaps(id=updated_beer.id, name=updated_beer.name, caps=caps)


@router.post("{beer_id}/caps", response_model=BeerCapResponse)
async def create_cap_existing_beer(
    beer_id: int,
    variant_name: Optional[str] = Form(None),
    file: UploadFile = File(...),
    beer_cap_facade: BeerCapFacade = Depends(get_beer_cap_facade),
):
    """
    Upload a beer cap image for an existing beer.
    """
    contents = await file.read()
    file_like = io.BytesIO(contents)

    cap_metadata = BeerCapCreateSchema(filename=file.filename, variant_name=variant_name)

    beer_cap = await beer_cap_facade.create_cap_for_existing_beer_and_upload(
        beer_id, cap_metadata, file_like, len(contents), file.content_type
    )

    if not beer_cap:
        raise HTTPException(status_code=404, detail="Beer not found.")

    url = beer_cap_facade.get_presigned_url_for_cap(beer_cap.s3_key)

    beer_response = BeerResponse(id=beer_cap.beer_id, name=beer_cap.beer.name)

    return BeerCapResponse(
        id=beer_cap.id,
        variant_name=beer_cap.variant_name,
        presigned_url=url,
        beer=beer_response,
    )
