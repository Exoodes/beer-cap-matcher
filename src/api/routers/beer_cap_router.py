import io
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.beer_cap.beer_cap_response import BeerCapResponse, BeerResponse
from src.api.schemas.beer_cap.update_schema import BeerCapUpdateSchema
from src.api.schemas.common.delete_status_response import DeleteStatusResponse
from src.db.crud.beer_cap import get_all_beer_caps, get_beer_cap_by_id, get_beer_caps_by_beer_id, update_beer_cap
from src.dependencies.db import get_db_session
from src.dependencies.facades import get_beer_cap_facade
from src.facades.beer_cap_facade import BeerCapFacade
from src.schemas.beer_cap_schema import BeerCapCreateSchema

router = APIRouter(prefix="/beer_caps", tags=["Beer Caps"])


@router.post("/", response_model=BeerCapResponse)
async def create_cap_with_new_beer(
    beer_name: str = Form(...),
    variant_name: Optional[str] = Form(None),
    file: UploadFile = File(...),
    beer_cap_facade: BeerCapFacade = Depends(get_beer_cap_facade),
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
async def api_get_all_beer_caps(
    beer_cap_facade: BeerCapFacade = Depends(get_beer_cap_facade),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Retrieve all beer caps with their presigned URLs.
    """

    beer_caps = await get_all_beer_caps(db, load_beer=True)

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
async def get_beer_cap(
    beer_cap_id: int,
    beer_cap_facade: BeerCapFacade = Depends(get_beer_cap_facade),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get a beer cap by ID, including its presigned URL.
    """

    beer_cap = await get_beer_cap_by_id(db, beer_cap_id, load_beer=True)
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
async def get_all_caps_from_beer(
    beer_id: int,
    beer_cap_facade: BeerCapFacade = Depends(get_beer_cap_facade),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Retrieve all beer caps for a specific beer ID.
    """

    beer_caps = await get_beer_caps_by_beer_id(db, beer_id, load_beer=True)

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
async def delete_beer_cap(
    beer_cap_id: int,
    beer_cap_facade: BeerCapFacade = Depends(get_beer_cap_facade),
):
    """
    Delete a beer cap and its augmented caps.
    """
    return_value = await beer_cap_facade.delete_beer_cap_and_its_augmented_caps(beer_cap_id)

    return DeleteStatusResponse(
        success=return_value,
        message="Beer cap and its augmented caps deleted successfully." if return_value else "Beer cap not found.",
    )


@router.patch("/{beer_cap_id}", response_model=BeerCapResponse)
async def update_beer_cap_endpoint(
    beer_cap_id: int,
    update_data: BeerCapUpdateSchema,
    beer_cap_facade: BeerCapFacade = Depends(get_beer_cap_facade),
    db: AsyncSession = Depends(get_db_session),
):
    updated_cap = await update_beer_cap(db, beer_cap_id, update_data, load_beer=True)

    if not updated_cap:
        raise HTTPException(status_code=404, detail="Beer cap not found")

    url = beer_cap_facade.get_presigned_url_for_cap(updated_cap.s3_key)
    beer_response = BeerResponse(id=updated_cap.beer_id, name=updated_cap.beer.name)

    return BeerCapResponse(
        id=updated_cap.id,
        variant_name=updated_cap.variant_name,
        presigned_url=url,
        beer=beer_response,
    )
