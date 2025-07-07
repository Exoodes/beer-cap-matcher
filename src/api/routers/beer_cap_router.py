import io
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from src.api.schemas.beer_cap.beer_cap_response import BeerCapResponse, BeerResponse
from src.api.schemas.common.delete_status_response import DeleteStatusResponse
from src.db.crud.beer_cap import get_all_beer_caps, get_beer_cap_by_id, get_beer_caps_by_beer_id
from src.db.database import GLOBAL_ASYNC_SESSION_MAKER
from src.facades.beer_cap_facade import BeerCapFacade
from src.schemas.beer_cap_schema import BeerCapCreateSchema
from src.storage.minio_client import MinioClientWrapper

router = APIRouter(prefix="/beer_cap", tags=["Beer Cap"])

minio_client = MinioClientWrapper()
beer_cap_facade = BeerCapFacade(minio_client)


@router.post("", response_model=BeerCapResponse)
async def create_cap_existing_beer(
    beer_id: int = Form(...),
    variant_name: Optional[str] = Form(None),
    file: UploadFile = File(...),
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


@router.post("/with_beer", response_model=BeerCapResponse)
async def create_cap_with_new_beer(
    beer_name: str = Form(...),
    variant_name: Optional[str] = Form(None),
    file: UploadFile = File(...),
):
    """
    Upload a beer cap image for a new beer (creates the beer entry as well).
    """
    contents = await file.read()
    file_like = io.BytesIO(contents)

    cap_metadata = BeerCapCreateSchema(filename=file.filename, variant_name=variant_name)

    beer_cap = await beer_cap_facade.create_beer_with_cap_and_upload(
        beer_name, cap_metadata, file_like, len(contents), file.content_type
    )

    url = beer_cap_facade.get_presigned_url_for_cap(beer_cap.s3_key)

    beer_response = BeerResponse(id=beer_cap.beer_id, name=beer_cap.beer.name)

    return BeerCapResponse(
        id=beer_cap.id,
        variant_name=beer_cap.variant_name,
        presigned_url=url,
        beer=beer_response,
    )


@router.get("", response_model=list[BeerCapResponse])
async def api_get_all_beer_caps():
    """
    Retrieve all beer caps with their presigned URLs.
    """

    async with GLOBAL_ASYNC_SESSION_MAKER() as session:
        beer_caps = await get_all_beer_caps(session, load_beer=True)

    result = []
    for beer_cap in beer_caps:
        url = beer_cap_facade.get_presigned_url_for_cap(beer_cap.s3_key)

        beer_response = BeerResponse(id=beer_cap.beer_id, name=beer_cap.beer.name)

        result.append(
            BeerCapResponse(
                id=beer_cap.id,
                variant_name=beer_cap.variant_name,
                presigned_url=url,
                beer=beer_response,
            )
        )

    return result


@router.get("/{beer_cap_id}", response_model=BeerCapResponse)
async def get_beer_cap(beer_cap_id: int):
    """
    Get a beer cap by ID, including its presigned URL.
    """

    async with GLOBAL_ASYNC_SESSION_MAKER() as session:
        beer_cap = await get_beer_cap_by_id(session, beer_cap_id, load_beer=True)
        if not beer_cap:
            raise HTTPException(status_code=404, detail="Beer cap not found.")

    url = beer_cap_facade.get_presigned_url_for_cap(beer_cap.s3_key)

    beer_response = BeerResponse(id=beer_cap.beer_id, name=beer_cap.beer.name)

    return BeerCapResponse(
        id=beer_cap.id,
        variant_name=beer_cap.variant_name,
        presigned_url=url,
        beer=beer_response,
    )


@router.get("/by_beer/{beer_id}", response_model=list[BeerCapResponse])
async def get_all_caps_from_beer(beer_id: int):
    """
    Retrieve all beer caps for a specific beer ID.
    """

    async with GLOBAL_ASYNC_SESSION_MAKER() as session:
        beer_caps = await get_beer_caps_by_beer_id(session, beer_id, load_beer=True)

    if not beer_caps:
        raise HTTPException(status_code=404, detail="No beer caps found for this beer.")

    result = []
    for beer_cap in beer_caps:
        url = beer_cap_facade.get_presigned_url_for_cap(beer_cap.s3_key)

        beer_response = BeerResponse(id=beer_cap.beer_id, name=beer_cap.beer.name)

        result.append(
            BeerCapResponse(
                id=beer_cap.id,
                variant_name=beer_cap.variant_name,
                presigned_url=url,
                beer=beer_response,
            )
        )

    return result


@router.delete("/{beer_cap_id}")
async def delete_beer_cap(beer_cap_id: int):
    """
    Delete a beer cap and its augmented caps.
    """
    return_value = await beer_cap_facade.delete_beer_cap_and_its_augmented_caps(beer_cap_id)

    return DeleteStatusResponse(
        success=return_value,
        message="Beer cap and its augmented caps deleted successfully." if return_value else "Beer cap not found.",
    )
