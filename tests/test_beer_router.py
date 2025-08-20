import importlib.util
import sys
import types

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Create lightweight dependency modules to avoid heavy imports
dependencies_pkg = types.ModuleType("src.api.dependencies")
dependencies_pkg.__path__ = []  # mark as package
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


class BeerCapFacade:  # dummy placeholder
    pass


beer_cap_facade_module.BeerCapFacade = BeerCapFacade
sys.modules["src.services.beer_cap_facade"] = beer_cap_facade_module

spec = importlib.util.spec_from_file_location(
    "beer_router", "src/api/routers/beer_router.py"
)
beer_router_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(beer_router_module)
beer_router = beer_router_module.router
from src.api.dependencies.db import get_db_session
from src.api.dependencies.facades import get_beer_cap_facade


class BeerStub:
    def __init__(
        self,
        id: int = 1,
        name: str = "Test Beer",
        rating: int = 0,
        caps=None,
        country=None,
    ):
        self.id = id
        self.name = name
        self.rating = rating
        self.caps = caps or []
        self.country = country


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(beer_router)

    async def override_db():
        yield None

    app.dependency_overrides[get_db_session] = override_db
    return TestClient(app)


def test_create_beer_success(client, monkeypatch):
    async def mock_create_beer(session, name, beer_brand_id, rating, country_id):
        return BeerStub(id=1, name=name, rating=rating)

    monkeypatch.setattr(beer_router_module, "create_beer", mock_create_beer)

    response = client.post("/beers/", json={"name": "Lager", "beer_brand_id": 1})
    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "name": "Lager",
        "rating": 0,
        "caps": [],
        "country": None,
    }


def test_get_all_beers_success(client, monkeypatch):
    async def mock_get_all_beers(session, load_caps=False, load_country=False):
        return [BeerStub()]

    monkeypatch.setattr(beer_router_module, "get_all_beers", mock_get_all_beers)

    response = client.get("/beers/")
    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "name": "Test Beer",
            "rating": 0,
            "caps": None,
            "country": None,
        }
    ]


def test_get_beer_by_id_success(client, monkeypatch):
    async def mock_get_beer_by_id(
        session, beer_id, load_caps=False, load_country=False
    ):
        return BeerStub(id=beer_id, name="Lager")

    monkeypatch.setattr(beer_router_module, "get_beer_by_id", mock_get_beer_by_id)

    response = client.get("/beers/1/")
    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "name": "Lager",
        "rating": 0,
        "caps": None,
        "country": None,
    }


def test_get_beer_by_id_not_found(client, monkeypatch):
    async def mock_get_beer_by_id(
        session, beer_id, load_caps=False, load_country=False
    ):
        return None

    monkeypatch.setattr(beer_router_module, "get_beer_by_id", mock_get_beer_by_id)

    response = client.get("/beers/1/")
    assert response.status_code == 404


def test_update_beer_success(client, monkeypatch):
    async def mock_update_beer(
        db, beer_cap_id, update_data, load_caps=True, load_country=True
    ):
        return BeerStub(id=beer_cap_id, name=update_data.name or "Updated")

    monkeypatch.setattr(beer_router_module, "update_beer", mock_update_beer)

    response = client.patch("/beers/1/?beer_cap_id=1", json={"name": "Updated"})
    assert response.status_code == 200
    assert response.json()["name"] == "Updated"


def test_update_beer_not_found(client, monkeypatch):
    async def mock_update_beer(
        db, beer_cap_id, update_data, load_caps=True, load_country=True
    ):
        return None

    monkeypatch.setattr(beer_router_module, "update_beer", mock_update_beer)

    response = client.patch("/beers/1/?beer_cap_id=1", json={"name": "Updated"})
    assert response.status_code == 404


def test_delete_beer_success(client):
    class Facade:
        async def delete_beer_and_caps(self, beer_id):
            return True

    client.app.dependency_overrides[get_beer_cap_facade] = lambda: Facade()

    response = client.delete("/beers/1/")
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_delete_beer_not_found(client):
    class Facade:
        async def delete_beer_and_caps(self, beer_id):
            return False

    client.app.dependency_overrides[get_beer_cap_facade] = lambda: Facade()

    response = client.delete("/beers/1/")
    assert response.status_code == 404
