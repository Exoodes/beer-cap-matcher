from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class QueryResultResponse(BaseModel):
    """
    Summary of similarity query results for a single beer cap match.
    Contains similarity metrics and match count.
    """

    mean_similarity: float = Field(
        ..., description="Average embedding similarity to the query"
    )
    min_similarity: float = Field(
        ..., description="Minimum embedding similarity to the query"
    )
    max_similarity: float = Field(
        ..., description="Maximum embedding similarity to the query"
    )
    match_count: int = Field(
        ..., description="Number of matched augmented caps for this beer cap"
    )

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class BeerCapResponseWithQueryResult(BaseModel):
    """
    Response schema representing a matched beer cap along with its similarity
    query result.
    """

    id: int = Field(..., description="ID of the matched beer cap")
    variant_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Variant name of the beer cap, if applicable",
    )
    collected_date: Optional[date] = Field(
        default=None,
        description="Date when this cap was collected",
    )
    presigned_url: str = Field(
        ..., description="Presigned URL to access the beer cap image"
    )
    query_result: QueryResultResponse = Field(
        ..., description="Similarity metrics for this result"
    )

    model_config = ConfigDict(from_attributes=True, extra="forbid")
