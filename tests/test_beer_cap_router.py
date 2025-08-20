import importlib.util
import sys
import types

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Minimal dependency modules
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

services_pkg = types.ModuleType("src.services")
services_pkg.__path__ = []
sys.modules.setdefault("src.services", services_pkg)

beer_cap_facade_module = types.ModuleType("src.services.beer_cap_facade")


class BeerCapFacade:
    pass


beer_cap_facade_module.BeerCapFacade = BeerCapFacade
sys.modules["src.services.beer_cap_facade"] = beer_cap_facade_module

spec = importlib.util.spec_from_file_location(
    "beer_cap_router", "src/api/routers/beer_cap_router.py"
)
beer_cap_router_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(beer_cap_router_module)
beer_cap_router = beer_cap_router_module.router
from src.api.dependencies.db import get_db_session
from src.api.dependencies.facades import get_beer_cap_facade


class DummyBeer:
    def __init__(self, id: int = 1, name: str = "Beer", rating: int = 5):
        self.id = id
        self.name = name
        self.rating = rating


class DummyBeerCap:
    def __init__(
        self, id: int = 1, variant_name: str = "Variant", beer: DummyBeer | None = None
    ):
        self.id = id
        self.variant_name = variant_name
        self.collected_date = None
        self.s3_key = "key"
        self.beer = beer or DummyBeer()
        self.beer_id = self.beer.id


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(beer_cap_router)

    async def override_db():
        yield None

    app.dependency_overrides[get_db_session] = override_db
    return TestClient(app)


def test_create_beer_cap_success(client):
    class Facade:
        async def create_cap_and_related_entities(
            self, cap_metadata, image_data, image_length, content_type
        ):
            return DummyBeerCap()

        def get_presigned_url_for_cap(self, s3_key):
            return "http://example.com/cap.jpg"

    client.app.dependency_overrides[get_beer_cap_facade] = lambda: Facade()

    files = {"file": ("cap.jpg", b"fake", "image/jpeg")}
    data = {"beer_id": "1"}
    response = client.post("/beer_caps/", files=files, data=data)
    assert response.status_code == 200
    assert response.json()["beer"]["id"] == 1


def test_get_all_beer_caps_success(client, monkeypatch):
    async def mock_get_all_beer_caps(db, load_beer=True):
        return [DummyBeerCap()]

    monkeypatch.setattr(
        beer_cap_router_module, "get_all_beer_caps", mock_get_all_beer_caps
    )

    class Facade:
        def get_presigned_url_for_cap(self, s3_key):
            return "http://example.com/cap.jpg"

    client.app.dependency_overrides[get_beer_cap_facade] = lambda: Facade()

    response = client.get("/beer_caps/")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_beer_cap_success(client, monkeypatch):
    async def mock_get_beer_cap_by_id(db, beer_cap_id, load_beer=True):
        return DummyBeerCap(id=beer_cap_id)

    monkeypatch.setattr(
        beer_cap_router_module, "get_beer_cap_by_id", mock_get_beer_cap_by_id
    )

    class Facade:
        def get_presigned_url_for_cap(self, s3_key):
            return "http://example.com/cap.jpg"

    client.app.dependency_overrides[get_beer_cap_facade] = lambda: Facade()

    response = client.get("/beer_caps/1/")
    assert response.status_code == 200
    assert response.json()["id"] == 1


def test_get_beer_cap_not_found(client, monkeypatch):
    async def mock_get_beer_cap_by_id(db, beer_cap_id, load_beer=True):
        return None

    monkeypatch.setattr(
        beer_cap_router_module, "get_beer_cap_by_id", mock_get_beer_cap_by_id
    )

    class Facade:
        def get_presigned_url_for_cap(self, s3_key):
            return "http://example.com/cap.jpg"

    client.app.dependency_overrides[get_beer_cap_facade] = lambda: Facade()

    response = client.get("/beer_caps/1/")
    assert response.status_code == 404


def test_update_beer_cap_success(client, monkeypatch):
    async def mock_update_beer_cap(db, beer_cap_id, update_data, load_beer=True):
        return DummyBeerCap(id=beer_cap_id, variant_name="Updated")

    monkeypatch.setattr(beer_cap_router_module, "update_beer_cap", mock_update_beer_cap)

    class Facade:
        def get_presigned_url_for_cap(self, s3_key):
            return "http://example.com/cap.jpg"

    client.app.dependency_overrides[get_beer_cap_facade] = lambda: Facade()

    response = client.patch("/beer_caps/1/", json={"variant_name": "Updated"})
    assert response.status_code == 200
    assert response.json()["variant_name"] == "Updated"


def test_update_beer_cap_not_found(client, monkeypatch):
    async def mock_update_beer_cap(db, beer_cap_id, update_data, load_beer=True):
        return None

    monkeypatch.setattr(beer_cap_router_module, "update_beer_cap", mock_update_beer_cap)

    class Facade:
        def get_presigned_url_for_cap(self, s3_key):
            return "http://example.com/cap.jpg"

    client.app.dependency_overrides[get_beer_cap_facade] = lambda: Facade()

    response = client.patch("/beer_caps/1/", json={"variant_name": "Updated"})
    assert response.status_code == 404


def test_delete_beer_cap_success(client):
    class Facade:
        async def delete_beer_cap_and_its_augmented_caps(self, cap_id):
            return True

    client.app.dependency_overrides[get_beer_cap_facade] = lambda: Facade()

    response = client.delete("/beer_caps/1/")
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_delete_beer_cap_not_found(client):
    class Facade:
        async def delete_beer_cap_and_its_augmented_caps(self, cap_id):
            return False

    client.app.dependency_overrides[get_beer_cap_facade] = lambda: Facade()

    response = client.delete("/beer_caps/1/")
    assert response.status_code == 404
