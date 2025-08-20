import sys
from contextlib import asynccontextmanager
from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from src.services.query_service import BeerCapNotFoundError, QueryService

sys.modules.setdefault("cv2", MagicMock())


@dataclass
class DummyAggregatedResult:
    match_count: int
    mean_similarity: float
    min_similarity: float
    max_similarity: float


@dataclass
class DummyBeerCap:
    id: int


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


@pytest.mark.asyncio
async def test_query_image_orders_and_filters_results(
    mock_minio_client_wrapper: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    @asynccontextmanager
    async def fake_session_maker():
        yield MagicMock()

    service = QueryService(
        minio_wrapper=mock_minio_client_wrapper, session_maker=fake_session_maker
    )

    all_results = {
        1: DummyAggregatedResult(
            match_count=1,
            mean_similarity=0.95,
            min_similarity=0.9,
            max_similarity=0.97,
        ),
        2: DummyAggregatedResult(
            match_count=2,
            mean_similarity=0.85,
            min_similarity=0.8,
            max_similarity=0.9,
        ),
        3: DummyAggregatedResult(
            match_count=3,
            mean_similarity=0.75,
            min_similarity=0.7,
            max_similarity=0.8,
        ),
    }

    class DummyQuerier:
        def query(self, image_bytes: bytes, top_k: int, faiss_k: int):
            assert top_k == 2
            ordered = dict(
                sorted(
                    all_results.items(),
                    key=lambda item: item[1].mean_similarity,
                    reverse=True,
                )[:top_k]
            )
            return ordered

    service.querier = DummyQuerier()

    async def fake_get_cap(session: MagicMock, cap_id: int):
        return DummyBeerCap(id=cap_id)

    monkeypatch.setattr("src.services.query_service.get_beer_cap_by_id", fake_get_cap)

    caps, agg_results = await service.query_image(b"dummy", top_k=2)

    expected_pairs = sorted(
        all_results.items(), key=lambda item: item[1].mean_similarity, reverse=True
    )[:2]

    assert len(caps) == len(agg_results) == 2
    for (cap, result), (exp_id, exp_result) in zip(
        zip(caps, agg_results), expected_pairs
    ):
        assert cap.id == exp_id
        assert result == exp_result
