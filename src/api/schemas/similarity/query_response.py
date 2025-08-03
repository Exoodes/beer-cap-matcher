from typing import Optional

from pydantic import BaseModel, ConfigDict


class QueryResultResponse(BaseModel):
    mean_distance: float
    min_distance: float
    max_distance: float
    match_count: int

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class BeerCapResponseWithQueryResult(BaseModel):
    id: int
    variant_name: Optional[str] = None
    presigned_url: str
    query_result: QueryResultResponse

    model_config = ConfigDict(from_attributes=True, extra="forbid")
