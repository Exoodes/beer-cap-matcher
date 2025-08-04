import logging
from typing import List

from fastapi import APIRouter, HTTPException, Query
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.constants.responses import INTERNAL_SERVER_ERROR_RESPONSE
from src.api.dependencies.db import get_db_session
from src.api.dependencies.facades import get_beer_cap_facade
from src.api.dependencies.services import get_cap_detection_service, reload_cap_detection_service_index
from src.api.schemas.augmented_beer_cap.augmented_beer_cap_response import AugmentedBeerCapResponse
from src.api.schemas.common.status_response import StatusResponse
from src.db.crud.augmented_cap_crud import get_all_augmented_caps
from src.services.beer_cap_facade import BeerCapFacade
from src.services.cap_detection_service import CapDetectionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/augmented_caps", tags=["Augmented Caps"])


@router.get(
    "/",
    response_model=List[AugmentedBeerCapResponse],
    responses=INTERNAL_SERVER_ERROR_RESPONSE,
)
async def get_all_beer_caps(
    db: AsyncSession = Depends(get_db_session),
) -> List[AugmentedBeerCapResponse]:
    """
    Retrieve all augmented beer caps.
    """
    augmented_caps = await get_all_augmented_caps(db)
    return [AugmentedBeerCapResponse(id=cap.id, embedding_vector=cap.embedding_vector) for cap in augmented_caps]


@router.delete(
    "/all/",
    response_model=StatusResponse,
    responses=INTERNAL_SERVER_ERROR_RESPONSE,
)
async def delete_all_augmented_caps(
    beer_cap_facade: BeerCapFacade = Depends(get_beer_cap_facade),
) -> StatusResponse:
    """
    Delete all augmented caps.
    """
    deleted_count = await beer_cap_facade.delete_all_augmented_caps()
    logger.info("Deleted %s augmented caps", deleted_count)
    return StatusResponse(success=True, message=f"Deleted {deleted_count} augmented caps")


@router.delete(
    "/{cap_id}/",
    response_model=StatusResponse,
    responses={
        404: {"description": "Cap not found"},
        **INTERNAL_SERVER_ERROR_RESPONSE,
    },
)
async def delete_augmented_cap(
    cap_id: int,
    beer_cap_facade: BeerCapFacade = Depends(get_beer_cap_facade),
) -> StatusResponse:
    """
    Delete a specific augmented cap by its ID.
    """
    success = await beer_cap_facade.delete_augmented_caps(cap_id)
    if not success:
        raise HTTPException(status_code=404, detail="Cap not found")
    logger.info("Deleted augmented cap with ID %s", cap_id)
    return StatusResponse(success=True, message="Augmented cap deleted")


@router.post(
    "/generate_all/",
    response_model=StatusResponse,
    responses=INTERNAL_SERVER_ERROR_RESPONSE,
)
async def generate_all_augmented_caps(
    augmentations_per_image: int = Query(..., gt=0, lt=100, description="Number of augmentations per image"),
    cap_detection_service: CapDetectionService = Depends(get_cap_detection_service),
) -> StatusResponse:
    """
    Generate all augmented images for caps.
    """
    generated_count = await cap_detection_service.preprocess(augmentations_per_image)
    logger.info("Generated %s augmented images", generated_count)
    return StatusResponse(success=True, message=f"Generated {generated_count} augmented images")


@router.post(
    "/generate_embeddings/",
    response_model=StatusResponse,
    responses=INTERNAL_SERVER_ERROR_RESPONSE,
)
async def generate_embeddings(
    cap_detection_service: CapDetectionService = Depends(get_cap_detection_service),
) -> StatusResponse:
    """
    Generate embeddings for all augmented caps.
    """
    embeddings_count = await cap_detection_service.generate_embeddings()
    logger.info("Generated %s embeddings", embeddings_count)
    return StatusResponse(success=True, message=f"Generated {embeddings_count} embeddings")


@router.post(
    "/generate_index/",
    response_model=StatusResponse,
    responses=INTERNAL_SERVER_ERROR_RESPONSE,
)
async def generate_index(
    cap_detection_service: CapDetectionService = Depends(get_cap_detection_service),
) -> StatusResponse:
    """
    Generate index for all augmented cap embeddings.
    """
    index_count = await cap_detection_service.generate_index()
    logger.info("Generated index for %s embeddings", index_count)
    reload_cap_detection_service_index()
    return StatusResponse(success=True, message=f"Generated index for {index_count} embeddings")
