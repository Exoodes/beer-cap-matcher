import importlib

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.dependencies.db import get_db_session
from src.api.dependencies.facades import get_beer_cap_facade
from src.api.dependencies.services import get_cap_detection_service

augmented_cap_router = importlib.import_module("src.api.routers.augmented_cap_router")


class CapDetectionStub:
    def __init__(self, preprocess_return: int = 0, embeddings_return: int = 0):
        self._pre = preprocess_return
        self._emb = embeddings_return

    async def preprocess(self, augmentations_per_image: int) -> int:
        return self._pre

    async def generate_embeddings(self) -> int:
        return self._emb


class BeerCapFacadeStub:
    def __init__(self, delete_return: bool = True):
        self._delete_return = delete_return

    async def delete_augmented_caps(self, cap_id: int) -> bool:
        return self._delete_return


@pytest.fixture()
def client() -> TestClient:
    app = FastAPI()
    app.include_router(augmented_cap_router.router)

    async def override_db():
        yield None

    app.dependency_overrides[get_db_session] = override_db
    return TestClient(app)


def test_generate_all_augmented_caps_success(client: TestClient) -> None:
    client.app.dependency_overrides[get_cap_detection_service] = (
        lambda: CapDetectionStub(preprocess_return=5)
    )
    resp = client.post("/augmented_caps/generate_all/?augmentations_per_image=1")
    assert resp.status_code == 200
    assert "Generated 5" in resp.json()["message"]


def test_get_all_augmented_beer_caps(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_get_all_augmented_caps(db, *, load_embedding_vector: bool = False):
        class AugCap:
            def __init__(self):
                self.id = 1
                self.embedding_vector = [0.1, 0.2]

        return [AugCap()]

    monkeypatch.setattr(
        augmented_cap_router,
        "get_all_augmented_caps",
        mock_get_all_augmented_caps,
    )

    resp = client.get("/augmented_caps/?include_embedding_vector=true")
    assert resp.status_code == 200
    assert resp.json() == [{"id": 1, "embedding_vector": [0.1, 0.2]}]


def test_generate_embeddings_success(client: TestClient) -> None:
    client.app.dependency_overrides[get_cap_detection_service] = (
        lambda: CapDetectionStub(embeddings_return=3)
    )
    resp = client.post("/augmented_caps/generate_embeddings/")
    assert resp.status_code == 200
    assert "Generated 3" in resp.json()["message"]


def test_delete_augmented_cap_success(client: TestClient) -> None:
    client.app.dependency_overrides[get_beer_cap_facade] = lambda: BeerCapFacadeStub(
        True
    )
    resp = client.delete("/augmented_caps/1/")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_delete_augmented_cap_not_found(client: TestClient) -> None:
    client.app.dependency_overrides[get_beer_cap_facade] = lambda: BeerCapFacadeStub(
        False
    )
    resp = client.delete("/augmented_caps/1/")
    assert resp.status_code == 404
