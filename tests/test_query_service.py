import pytest
from contextlib import asynccontextmanager
from dataclasses import dataclass
from unittest.mock import MagicMock

from src.services.query_service import BeerCapNotFoundError, QueryService


@dataclass
class DummyAggregatedResult:
    match_count: int
    mean_similarity: float
    min_similarity: float
    max_similarity: float


@pytest.mark.asyncio
async def test_query_image_raises_when_cap_missing(
    mock_minio_client_wrapper: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    @asynccontextmanager
    async def fake_session_maker():
        yield MagicMock()

    service = QueryService(
        minio_wrapper=mock_minio_client_wrapper, session_maker=fake_session_maker
    )

    mock_querier = MagicMock()
    mock_querier.query.return_value = {
        1: DummyAggregatedResult(
            match_count=1,
            mean_similarity=0.9,
            min_similarity=0.8,
            max_similarity=1.0,
        )
    }
    service.querier = mock_querier

    async def fake_get_cap(session: MagicMock, cap_id: int):
        return None

    monkeypatch.setattr("src.services.query_service.get_beer_cap_by_id", fake_get_cap)

    with pytest.raises(BeerCapNotFoundError):
        await service.query_image(b"dummy")
