from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from src.api.schemas.beer_cap import BeerCapResponse
from src.facades.beer_cap_facade import BeerCapFacade
from src.storage.minio_client import MinioClientWrapper

router = APIRouter(prefix="/beer_cap", tags=["Beer Cap"])

minio_client = MinioClientWrapper()
beer_cap_facade = BeerCapFacade(minio_client)


@router.post("/", response_model=BeerCapResponse)
async def create_cap_existing_beer(
    beer_id: int = Form(...),
    variant_name: Optional[str] = Form(None),
    file: UploadFile = File(...),
):
    """
    Upload a beer cap image for an existing beer.
    """
    contents = await file.read()

    from src.schemas.beer_cap_schema import BeerCapCreateSchema

    cap_metadata = BeerCapCreateSchema(filename=file.filename, variant_name=variant_name)

    beer_cap = await beer_cap_facade.create_cap_for_existing_beer_and_upload(
        beer_id, cap_metadata, contents, len(contents), file.content_type
    )

    if not beer_cap:
        raise HTTPException(status_code=404, detail="Beer not found.")

    url = beer_cap_facade.get_presigned_url_for_cap(beer_cap.s3_key)

    return BeerCapResponse(
        id=beer_cap.id,
        beer_id=beer_cap.beer_id,
        variant_name=beer_cap.variant_name,
        s3_key=beer_cap.s3_key,
        presigned_url=url,
    )


@router.post("/with_beer/", response_model=BeerCapResponse)
async def create_cap_with_new_beer(
    beer_name: str = Form(...),
    variant_name: Optional[str] = Form(None),
    file: UploadFile = File(...),
):
    """
    Upload a beer cap image for a new beer (creates the beer entry as well).
    """
    contents = await file.read()

    from src.schemas.beer_cap_schema import BeerCapCreateSchema

    cap_metadata = BeerCapCreateSchema(filename=file.filename, variant_name=variant_name)

    beer_cap = await beer_cap_facade.create_beer_with_cap_and_upload(
        beer_name, cap_metadata, contents, len(contents), file.content_type
    )

    url = beer_cap_facade.get_presigned_url_for_cap(beer_cap.s3_key)

    return BeerCapResponse(
        id=beer_cap.id,
        beer_id=beer_cap.beer_id,
        variant_name=beer_cap.variant_name,
        s3_key=beer_cap.s3_key,
        presigned_url=url,
    )


@router.get("/{beer_cap_id}", response_model=BeerCapResponse)
async def get_beer_cap(beer_cap_id: int):
    """
    Get a beer cap by ID, including its presigned URL.
    """
    from src.db.crud.beer_cap import get_beer_cap_by_id
    from src.db.database import GLOBAL_ASYNC_SESSION_MAKER

    async with GLOBAL_ASYNC_SESSION_MAKER() as session:
        beer_cap = await get_beer_cap_by_id(session, beer_cap_id)
        if not beer_cap:
            raise HTTPException(status_code=404, detail="Beer cap not found.")

    url = beer_cap_facade.get_presigned_url_for_cap(beer_cap.s3_key)

    return BeerCapResponse(
        id=beer_cap.id,
        beer_id=beer_cap.beer_id,
        variant_name=beer_cap.variant_name,
        s3_key=beer_cap.s3_key,
        presigned_url=url,
    )


@router.delete("/{beer_cap_id}")
async def delete_beer_cap(beer_cap_id: int):
    """
    Delete a beer cap and its augmented caps.
    """
    await beer_cap_facade.delete_beer_cap_and_its_augmented_caps(beer_cap_id)
    return {"message": "Beer cap deleted successfully"}
