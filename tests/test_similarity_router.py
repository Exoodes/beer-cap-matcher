import types
import sys
from dataclasses import dataclass
from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

# Stub out heavy cap detection service dependencies to avoid OpenCV import
cap_detection_stub = types.ModuleType("src.services.cap_detection_service")
cap_detection_stub.CapDetectionService = type("CapDetectionService", (), {})
sys.modules["src.services.cap_detection_service"] = cap_detection_stub

from src.api.routers.similarity_router import router
from src.api.dependencies.services import get_query_service
from src.api.dependencies.facades import get_beer_cap_facade
from src.api.schemas.similarity.query_response import BeerCapResponseWithQueryResult


@dataclass
class DummyBeerCap:
    id: int
    s3_key: str
    variant_name: str | None = None
    collected_date: date | None = None


@dataclass
class DummyAggregatedResult:
    match_count: int
    mean_similarity: float
    min_similarity: float
    max_similarity: float


@pytest.fixture()
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)

    cap = DummyBeerCap(
        id=1,
        s3_key="test.jpg",
        variant_name="Test Cap",
        collected_date=date(2023, 1, 1),
    )
    result = DummyAggregatedResult(
        match_count=1,
        mean_similarity=0.9,
        min_similarity=0.8,
        max_similarity=1.0,
    )

    mock_query_service = MagicMock()
    mock_query_service.query_image = AsyncMock(return_value=([cap], [result]))
    mock_facade = MagicMock()
    mock_facade.get_presigned_url_for_cap.return_value = "http://example.com/test.jpg"

    app.dependency_overrides[get_query_service] = lambda: mock_query_service
    app.dependency_overrides[get_beer_cap_facade] = lambda: mock_facade

    return TestClient(app)


def test_query_image_success(client: TestClient) -> None:
    with open("tests/data/test_image.jpg", "rb") as f:
        files = {"file": ("test_image.jpg", f, "image/jpeg")}
        response = client.post(
            "/similarity/query-image", files=files, params={"top_k": 1}
        )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list) and len(data) == 1
    parsed = [BeerCapResponseWithQueryResult.model_validate(item) for item in data]

    item = parsed[0]
    assert item.id == 1
    assert item.variant_name == "Test Cap"
    assert item.collected_date == date(2023, 1, 1)
    assert item.presigned_url == "http://example.com/test.jpg"
    assert item.query_result.match_count == 1
    assert item.query_result.mean_similarity == 0.9
    assert item.query_result.min_similarity == 0.8
    assert item.query_result.max_similarity == 1.0


def test_query_image_rejects_non_image_file(client: TestClient) -> None:
    files = {"file": ("not_image.txt", b"text content", "text/plain")}
    response = client.post("/similarity/query-image", files=files)

    assert response.status_code == 400
    assert response.json()["detail"] == "Only image uploads are allowed."


def test_query_image_missing_file(client: TestClient) -> None:
    response = client.post("/similarity/query-image")
    assert response.status_code == 422
