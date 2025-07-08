from fastapi import APIRouter, HTTPException
from fastapi.params import Depends

from src.api.schemas.common.delete_status_response import DeleteStatusResponse
from src.dependencies.facades import get_beer_cap_facade
from src.facades.beer_cap_facade import BeerCapFacade

router = APIRouter(prefix="/augmented_caps", tags=["Augmented Caps"])


@router.delete("/{cap_id}", response_model=DeleteStatusResponse)
async def delete_augmented_cap(cap_id: int, beer_cap_facade: BeerCapFacade = Depends(get_beer_cap_facade)):
    """
    Delete a specific augmented cap by its ID.
    """
    success = await beer_cap_facade.delete_augmented_caps(cap_id)
    if not success:
        raise HTTPException(status_code=404, detail="Cap not found")
    return DeleteStatusResponse(success=True, message="Augmented cap deleted")


@router.delete("/", response_model=DeleteStatusResponse)
async def delete_all_augmented_caps(beer_cap_facade: BeerCapFacade = Depends(get_beer_cap_facade)):
    """
    Delete all augmented caps.
    """
    deleted_count = await beer_cap_facade.delete_all_augmented_caps()
    return DeleteStatusResponse(success=True, message=f"Deleted {deleted_count} augmented caps")
