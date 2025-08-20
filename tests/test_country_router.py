import pytest
import importlib.util
import sys
import types

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.dependencies.db import get_db_session

# Stub dependencies
dependencies_pkg = types.ModuleType("src.api.dependencies")
sys.modules.setdefault("src.api.dependencies", dependencies_pkg)

db_module = types.ModuleType("src.api.dependencies.db")


async def dummy_get_db_session():
    pass


db_module.get_db_session = dummy_get_db_session
sys.modules["src.api.dependencies.db"] = db_module

spec = importlib.util.spec_from_file_location(
    "country_router", "src/api/routers/country_router.py"
)
country_router_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(country_router_module)
country_router = country_router_module.router


class CountryStub:
    def __init__(
        self, id: int = 1, name: str = "Country", description: str = "Desc", beers=None
    ):
        self.id = id
        self.name = name
        self.description = description
        self.beers = beers or []


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(country_router)

    async def override_db():
        yield None

    app.dependency_overrides[get_db_session] = override_db
    return TestClient(app)


def test_create_country_success(client, monkeypatch):
    async def mock_create_country(db, country_data):
        return CountryStub(
            id=1, name=country_data.name, description=country_data.description
        )

    monkeypatch.setattr(country_router_module, "create_country", mock_create_country)

    response = client.post("/countries/", data={"name": "A", "description": "D"})
    assert response.status_code == 200
    assert response.json() == {"id": 1, "name": "A", "description": "D", "beers": []}


def test_get_all_countries_success(client, monkeypatch):
    async def mock_get_all_countries(db, load_beers=False):
        return [CountryStub()]

    monkeypatch.setattr(
        country_router_module, "get_all_countries", mock_get_all_countries
    )

    response = client.get("/countries/")
    assert response.status_code == 200
    assert response.json() == [
        {"id": 1, "name": "Country", "description": "Desc", "beers": None}
    ]


def test_get_country_by_id_success(client, monkeypatch):
    async def mock_get_country_by_id(db, country_id, load_beers=False):
        return CountryStub(id=country_id)

    monkeypatch.setattr(
        country_router_module, "get_country_by_id", mock_get_country_by_id
    )

    response = client.get("/countries/1/")
    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "name": "Country",
        "description": "Desc",
        "beers": None,
    }


def test_get_country_by_id_not_found(client, monkeypatch):
    async def mock_get_country_by_id(db, country_id, load_beers=False):
        return None

    monkeypatch.setattr(
        country_router_module, "get_country_by_id", mock_get_country_by_id
    )

    response = client.get("/countries/1/")
    assert response.status_code == 404


def test_update_country_success(client, monkeypatch):
    async def mock_update_country(db, country_id, update_data, load_beers=True):
        return CountryStub(
            id=country_id,
            name=update_data.name or "Updated",
            description=update_data.description or "Desc",
        )

    monkeypatch.setattr(country_router_module, "update_country", mock_update_country)

    response = client.patch("/countries/1/", json={"name": "Updated"})
    assert response.status_code == 200
    assert response.json()["name"] == "Updated"


def test_update_country_not_found(client, monkeypatch):
    async def mock_update_country(db, country_id, update_data, load_beers=True):
        return None

    monkeypatch.setattr(country_router_module, "update_country", mock_update_country)

    response = client.patch("/countries/1/", json={"name": "Updated"})
    assert response.status_code == 404


def test_delete_country_success(client, monkeypatch):
    async def mock_get_country_by_id(db, country_id):
        return CountryStub(id=country_id)

    async def mock_delete_country(db, country_id):
        return True

    monkeypatch.setattr(
        country_router_module, "get_country_by_id", mock_get_country_by_id
    )
    monkeypatch.setattr(country_router_module, "delete_country", mock_delete_country)

    response = client.delete("/countries/1/")
    assert response.status_code == 200
    assert response.json()["id"] == 1


def test_delete_country_not_found(client, monkeypatch):
    async def mock_get_country_by_id(db, country_id):
        return None

    monkeypatch.setattr(
        country_router_module, "get_country_by_id", mock_get_country_by_id
    )

    response = client.delete("/countries/1/")
    assert response.status_code == 404
