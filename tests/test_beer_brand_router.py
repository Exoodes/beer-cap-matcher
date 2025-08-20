import pytest
import importlib.util
import sys
import types

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.dependencies.db import get_db_session

# Stub dependency modules
dependencies_pkg = types.ModuleType("src.api.dependencies")
sys.modules.setdefault("src.api.dependencies", dependencies_pkg)

db_module = types.ModuleType("src.api.dependencies.db")


async def dummy_get_db_session():
    pass


db_module.get_db_session = dummy_get_db_session
sys.modules["src.api.dependencies.db"] = db_module

spec = importlib.util.spec_from_file_location(
    "beer_brand_router", "src/api/routers/beer_brand_router.py"
)
beer_brand_router_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(beer_brand_router_module)
beer_brand_router = beer_brand_router_module.router


class BeerBrandStub:
    def __init__(self, id: int = 1, name: str = "Brand", beers=None):
        self.id = id
        self.name = name
        self.beers = beers or []


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(beer_brand_router)

    async def override_db():
        yield None

    app.dependency_overrides[get_db_session] = override_db
    return TestClient(app)


def test_create_beer_brand_success(client, monkeypatch):
    async def mock_create_beer_brand(db, name):
        return BeerBrandStub(id=1, name=name)

    monkeypatch.setattr(
        beer_brand_router_module, "create_beer_brand", mock_create_beer_brand
    )

    response = client.post("/beer_brands/", data={"name": "Brand"})
    assert response.status_code == 200
    assert response.json() == {"id": 1, "name": "Brand", "beers": []}


def test_get_all_beer_brands_success(client, monkeypatch):
    async def mock_get_all_beer_brands(db, load_beers=False):
        return [BeerBrandStub()]

    monkeypatch.setattr(
        beer_brand_router_module, "get_all_beer_brands", mock_get_all_beer_brands
    )

    response = client.get("/beer_brands/")
    assert response.status_code == 200
    assert response.json() == [{"id": 1, "name": "Brand", "beers": None}]


def test_get_beer_brand_by_id_success(client, monkeypatch):
    async def mock_get_by_id(db, beer_brand_id, load_beers=False):
        return BeerBrandStub(id=beer_brand_id)

    monkeypatch.setattr(
        beer_brand_router_module, "get_beer_brand_by_id", mock_get_by_id
    )

    response = client.get("/beer_brands/1/")
    assert response.status_code == 200
    assert response.json() == {"id": 1, "name": "Brand", "beers": None}


def test_get_beer_brand_by_id_not_found(client, monkeypatch):
    async def mock_get_by_id(db, beer_brand_id, load_beers=False):
        return None

    monkeypatch.setattr(
        beer_brand_router_module, "get_beer_brand_by_id", mock_get_by_id
    )

    response = client.get("/beer_brands/1/")
    assert response.status_code == 404


def test_update_beer_brand_success(client, monkeypatch):
    async def mock_update_beer_brand(db, beer_brand_id, update_data, load_beers=True):
        return BeerBrandStub(id=beer_brand_id, name=update_data.name or "Updated")

    monkeypatch.setattr(
        beer_brand_router_module, "update_beer_brand", mock_update_beer_brand
    )

    response = client.patch("/beer_brands/1/", json={"name": "Updated"})
    assert response.status_code == 200
    assert response.json()["name"] == "Updated"


def test_update_beer_brand_not_found(client, monkeypatch):
    async def mock_update_beer_brand(db, beer_brand_id, update_data, load_beers=True):
        return None

    monkeypatch.setattr(
        beer_brand_router_module, "update_beer_brand", mock_update_beer_brand
    )

    response = client.patch("/beer_brands/1/", json={"name": "Updated"})
    assert response.status_code == 404


def test_delete_beer_brand_success(client, monkeypatch):
    async def mock_delete_beer_brand(db, beer_brand_id):
        return True

    monkeypatch.setattr(
        beer_brand_router_module, "delete_beer_brand", mock_delete_beer_brand
    )

    response = client.delete("/beer_brands/1/")
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_delete_beer_brand_not_found(client, monkeypatch):
    async def mock_delete_beer_brand(db, beer_brand_id):
        return False

    monkeypatch.setattr(
        beer_brand_router_module, "delete_beer_brand", mock_delete_beer_brand
    )

    response = client.delete("/beer_brands/1/")
    assert response.status_code == 404
