from typing import List

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.db import get_db_session
from src.api.dependencies.facades import get_beer_cap_facade
from src.api.dependencies.services import get_cap_detection_service
from src.api.schemas.augmented_beer_cap.augmented_beer_cap_response import AugmentedBeerCapResponse
from src.api.schemas.common.delete_status_response import StatusResponse
from src.db.crud.augmented_cap import get_all_augmented_caps
from src.facades.beer_cap_facade import BeerCapFacade
from src.services.cap_detection_service import CapDetectionService

router = APIRouter(prefix="/augmented_caps", tags=["Augmented Caps"])


@router.get(
    "/", response_model=List[AugmentedBeerCapResponse], responses={500: {"description": "Internal server error"}}
)
async def get_all_beer_caps(
    db: AsyncSession = Depends(get_db_session),
):
    """
    Retrieve all augmented beer caps.
    """
    augmented_caps = await get_all_augmented_caps(db)

    result = []
    for cap in augmented_caps:
        result.append(AugmentedBeerCapResponse(id=cap.id, embedding_vector=cap.embedding_vector))

    return result


@router.delete(
    "/{cap_id}/",
    response_model=StatusResponse,
    responses={404: {"description": "Cap not found"}, 500: {"description": "Internal server error"}},
)
async def delete_augmented_cap(cap_id: int, beer_cap_facade: BeerCapFacade = Depends(get_beer_cap_facade)):
    """
    Delete a specific augmented cap by its ID.
    """
    success = await beer_cap_facade.delete_augmented_caps(cap_id)
    if not success:
        raise HTTPException(status_code=404, detail="Cap not found")
    return StatusResponse(success=True, message="Augmented cap deleted")


@router.delete("/", response_model=StatusResponse, responses={500: {"description": "Internal server error"}})
async def delete_all_augmented_caps(beer_cap_facade: BeerCapFacade = Depends(get_beer_cap_facade)):
    """
    Delete all augmented caps.
    """
    deleted_count = await beer_cap_facade.delete_all_augmented_caps()
    return StatusResponse(success=True, message=f"Deleted {deleted_count} augmented caps")


@router.post(
    "/generate_all/",
    response_model=StatusResponse,
    responses={500: {"description": "Internal server error"}},
)
async def generate_all_augmented_caps(cap_detection_service: CapDetectionService = Depends(get_cap_detection_service)):
    """
    Generate all augmented images for caps.
    """
    generated_count = await cap_detection_service.preprocess()
    return StatusResponse(success=True, message=f"Generated {generated_count} augmented images")


@router.post(
    "/generate_embeddings/",
    response_model=StatusResponse,
    responses={500: {"description": "Internal server error"}},
)
async def generate_embeddings(cap_detection_service: CapDetectionService = Depends(get_cap_detection_service)):
    """
    Generate embeddings for all augmented caps.
    """
    embeddings_count = await cap_detection_service.generate_embeddings()
    return StatusResponse(success=True, message=f"Generated {embeddings_count} embeddings")


@router.post(
    "/generate_index/",
    response_model=StatusResponse,
    responses={500: {"description": "Internal server error"}},
)
async def generate_index(cap_detection_service: CapDetectionService = Depends(get_cap_detection_service)):
    """
    Generate index for all augmented cap embeddings.
    """
    index_count = await cap_detection_service.generate_index()
    return StatusResponse(success=True, message=f"Generated index for {index_count} embeddings")
