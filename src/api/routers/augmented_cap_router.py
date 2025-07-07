from fastapi import APIRouter, HTTPException

from src.api.schemas.common.delete_status_response import DeleteStatusResponse
from src.facades.beer_cap_facade import BeerCapFacade
from src.storage.minio_client import MinioClientWrapper

router = APIRouter(prefix="/augmented_caps", tags=["Augmented Caps"])

minio_client = MinioClientWrapper()
beer_cap_facade = BeerCapFacade(minio_client)


@router.delete("/{cap_id}", response_model=DeleteStatusResponse)
async def delete_augmented_cap(cap_id: int):
    success = await beer_cap_facade.delete_augmented_caps(cap_id)
    if not success:
        raise HTTPException(status_code=404, detail="Cap not found")
    return DeleteStatusResponse(success=True, message="Augmented caps deleted")


@router.delete("/", response_model=DeleteStatusResponse)
async def delete_all_augmented_caps():
    deleted_count = await beer_cap_facade.delete_all_augmented_caps()
    return DeleteStatusResponse(success=True, message=f"Deleted {deleted_count} augmented caps")
