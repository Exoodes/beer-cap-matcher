import pytest
import importlib.util
import sys
import types

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Stub dependency modules
dependencies_pkg = types.ModuleType("src.api.dependencies")
dependencies_pkg.__path__ = []
sys.modules.setdefault("src.api.dependencies", dependencies_pkg)

db_module = types.ModuleType("src.api.dependencies.db")


async def dummy_get_db_session():
    pass


db_module.get_db_session = dummy_get_db_session
sys.modules["src.api.dependencies.db"] = db_module

facades_module = types.ModuleType("src.api.dependencies.facades")


def dummy_get_beer_cap_facade():
    pass


facades_module.get_beer_cap_facade = dummy_get_beer_cap_facade
sys.modules["src.api.dependencies.facades"] = facades_module

services_module = types.ModuleType("src.api.dependencies.services")


def dummy_get_cap_detection_service(request=None):
    return None


async def dummy_reload_query_service_index(request):
    pass


services_module.get_cap_detection_service = dummy_get_cap_detection_service
services_module.reload_query_service_index = dummy_reload_query_service_index
sys.modules["src.api.dependencies.services"] = services_module

services_pkg = types.ModuleType("src.services")
services_pkg.__path__ = []
sys.modules.setdefault("src.services", services_pkg)

beer_cap_facade_module = types.ModuleType("src.services.beer_cap_facade")


class BeerCapFacade:
    pass


beer_cap_facade_module.BeerCapFacade = BeerCapFacade
sys.modules["src.services.beer_cap_facade"] = beer_cap_facade_module

cap_detection_module = types.ModuleType("src.services.cap_detection_service")


class CapDetectionService:
    pass


cap_detection_module.CapDetectionService = CapDetectionService
sys.modules["src.services.cap_detection_service"] = cap_detection_module

from src.api.dependencies.db import get_db_session
from src.api.dependencies.facades import get_beer_cap_facade
from src.api.dependencies.services import get_cap_detection_service

spec = importlib.util.spec_from_file_location(
    "augmented_cap_router", "src/api/routers/augmented_cap_router.py"
)
augmented_cap_router_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(augmented_cap_router_module)
augmented_cap_router = augmented_cap_router_module.router


class CapDetectionStub:
    def __init__(self, preprocess_return=0, embeddings_return=0):
        self._pre = preprocess_return
        self._emb = embeddings_return

    async def preprocess(self, augmentations_per_image: int):
        return self._pre

    async def generate_embeddings(self):
        return self._emb


class BeerCapFacadeStub:
    def __init__(self, delete_return=True):
        self._delete_return = delete_return

    async def delete_augmented_caps(self, cap_id: int):
        return self._delete_return


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(augmented_cap_router)

    async def override_db():
        yield None

    app.dependency_overrides[get_db_session] = override_db
    return TestClient(app)


def test_generate_all_augmented_caps_success(client):
    client.app.dependency_overrides[get_cap_detection_service] = (
        lambda: CapDetectionStub(preprocess_return=5)
    )

    response = client.post("/augmented_caps/generate_all/?augmentations_per_image=1")
    assert response.status_code == 200
    assert "Generated 5" in response.json()["message"]


def test_get_all_augmented_caps(client, monkeypatch):
    async def mock_get_all_augmented_caps(db):
        class AugCap:
            def __init__(self):
                self.id = 1
                self.embedding_vector = [0.1, 0.2]

        return [AugCap()]

    monkeypatch.setattr(
        augmented_cap_router_module,
        "get_all_augmented_caps",
        mock_get_all_augmented_caps,
    )

    response = client.get("/augmented_caps/?include_embedding_vector=true")
    assert response.status_code == 200
    assert response.json() == [{"id": 1, "embedding_vector": [0.1, 0.2]}]


def test_generate_embeddings_success(client):
    client.app.dependency_overrides[get_cap_detection_service] = (
        lambda: CapDetectionStub(embeddings_return=3)
    )

    response = client.post("/augmented_caps/generate_embeddings/")
    assert response.status_code == 200
    assert "Generated 3" in response.json()["message"]


def test_delete_augmented_cap_success(client):
    client.app.dependency_overrides[get_beer_cap_facade] = lambda: BeerCapFacadeStub(
        True
    )

    response = client.delete("/augmented_caps/1/")
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_delete_augmented_cap_not_found(client):
    client.app.dependency_overrides[get_beer_cap_facade] = lambda: BeerCapFacadeStub(
        False
    )

    response = client.delete("/augmented_caps/1/")
    assert response.status_code == 404
