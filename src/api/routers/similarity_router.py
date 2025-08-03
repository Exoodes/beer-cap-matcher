from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from src.api.dependencies.facades import get_beer_cap_facade
from src.api.dependencies.services import get_cap_detection_service
from src.api.schemas.similarity.query_response import BeerCapResponseWithQueryResult, QueryResultResponse
from src.services.beer_cap_facade import BeerCapFacade
from src.services.cap_detection_service import CapDetectionService

router = APIRouter(prefix="/similarity", tags=["Similarity"])


@router.post(
    "/query-image",
    response_model=List[BeerCapResponseWithQueryResult],
    responses={400: {"description": "Invalid image format"}, 500: {"description": "Internal server error"}},
)
async def query_image(
    file: UploadFile = File(...),
    cap_detection_service: CapDetectionService = Depends(get_cap_detection_service),
    beer_cap_facade: BeerCapFacade = Depends(get_beer_cap_facade),
):
    image_bytes = await file.read()
    caps, query_results = await cap_detection_service.query_image(image_bytes=image_bytes)

    assert len(caps) == len(query_results), "Mismatch between caps and query results length"

    responses = []
    for cap, cap_query_result in zip(caps, query_results):
        url = beer_cap_facade.get_presigned_url_for_cap(cap.s3_key)

        query_result_response = QueryResultResponse(
            mean_distance=cap_query_result.mean_distance,
            min_distance=cap_query_result.min_distance,
            max_distance=cap_query_result.max_distance,
            match_count=cap_query_result.match_count,
        )

        responses.append(
            BeerCapResponseWithQueryResult(
                id=cap.id,
                variant_name=cap.variant_name,
                presigned_url=url,
                query_result=query_result_response,
            )
        )

    return responses
