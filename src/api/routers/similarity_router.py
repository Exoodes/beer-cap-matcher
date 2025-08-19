import logging
from datetime import date
from typing import Annotated, Any, List, Mapping, Optional, cast

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from src.api.constants.responses import INTERNAL_SERVER_ERROR_RESPONSE, ResponseDict
from src.api.dependencies.facades import get_beer_cap_facade
from src.api.dependencies.services import get_query_service
from src.api.schemas.similarity.query_response import (
    BeerCapResponseWithQueryResult,
    QueryResultResponse,
)
from src.services.beer_cap_facade import BeerCapFacade
from src.services.query_service import QueryService

logger = logging.getLogger(__name__)

BAD_REQUEST_RESPONSE: ResponseDict = {400: {"description": "Invalid image format"}}

router = APIRouter(prefix="/similarity", tags=["Similarity"])


@router.post(
    "/query-image",
    response_model=List[BeerCapResponseWithQueryResult],
    responses={
        **BAD_REQUEST_RESPONSE,
        **cast(Mapping[int | str, dict[str, Any]], INTERNAL_SERVER_ERROR_RESPONSE),
    },
)
async def query_image(
    query_service: Annotated[QueryService, Depends(get_query_service)],
    beer_cap_facade: Annotated[BeerCapFacade, Depends(get_beer_cap_facade)],
    file: UploadFile = File(...),
    top_k: int = Query(3, gt=0, le=15, description="Number of top matches to return"),
    faiss_k: int = Query(
        10000, gt=0, description="Number of FAISS candidates to search"
    ),
) -> List[BeerCapResponseWithQueryResult]:
    """
    Query the most similar beer caps to the uploaded image.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are allowed.")

    image_bytes = await file.read()

    logger.info(
        "Received similarity query: file=%s, top_k=%s, faiss_k=%s",
        file.filename,
        top_k,
        faiss_k,
    )

    caps, query_results = await query_service.query_image(
        image_bytes=image_bytes,
        top_k=top_k,
        faiss_k=faiss_k,
    )

    if len(caps) != len(query_results):
        raise HTTPException(
            status_code=500, detail="Mismatch between results and metadata."
        )

    return [
        BeerCapResponseWithQueryResult(
            id=cap.id,
            variant_name=cap.variant_name,
            collected_date=cast(Optional[date], cap.collected_date),
            presigned_url=beer_cap_facade.get_presigned_url_for_cap(cap.s3_key),
            query_result=QueryResultResponse(
                mean_similarity=result.mean_similarity,
                min_similarity=result.min_similarity,
                max_similarity=result.max_similarity,
                match_count=result.match_count,
            ),
        )
        for cap, result in zip(caps, query_results)
    ]
