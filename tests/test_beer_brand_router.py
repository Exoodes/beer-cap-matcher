import importlib
from typing import Optional

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.dependencies.db import get_db_session

beer_brand_router = importlib.import_module("src.api.routers.beer_brand_router")


@pytest.fixture()
def client() -> TestClient:
    app = FastAPI()
    app.include_router(beer_brand_router.router)

    async def override_db():
        yield None

    app.dependency_overrides[get_db_session] = override_db
    return TestClient(app)


class _Brand:
    def __init__(self, id: int, name: str, beers: Optional[list] = None):
        self.id = id
        self.name = name
        self.beers = beers


def test_create_beer_brand_success(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_create_brand(db, name: str):
        return _Brand(id=1, name=name, beers=[])

    monkeypatch.setattr(beer_brand_router, "create_beer_brand", mock_create_brand)

    resp = client.post("/beer_brands/", data={"name": "BrandX"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 1
    assert data["name"] == "BrandX"
    assert "beers" in data


def test_list_beer_brands(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def mock_get_all(db, *, load_beers: bool = False):
        return [
            _Brand(id=1, name="BrandA", beers=[] if load_beers else None),
            _Brand(id=2, name="BrandB", beers=[] if load_beers else None),
        ]

    monkeypatch.setattr(beer_brand_router, "get_all_beer_brands", mock_get_all)

    resp = client.get("/beer_brands/")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list) and len(data) == 2
    assert {item["name"] for item in data} == {"BrandA", "BrandB"}


def test_get_beer_brand_by_id_found(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_get_by_id(db, beer_brand_id: int, *, load_beers: bool = False):
        return _Brand(id=beer_brand_id, name="BrandA", beers=[] if load_beers else None)

    monkeypatch.setattr(beer_brand_router, "get_beer_brand_by_id", mock_get_by_id)

    resp = client.get("/beer_brands/1/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 1
    assert data["name"] == "BrandA"


def test_get_beer_brand_by_id_not_found(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_get_by_id(db, beer_brand_id: int, *, load_beers: bool = False):
        return None

    monkeypatch.setattr(beer_brand_router, "get_beer_brand_by_id", mock_get_by_id)

    resp = client.get("/beer_brands/9999/")
    assert resp.status_code == 404


def test_update_beer_brand_success(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_update_brand(
        db, beer_brand_id: int, update_data, *, load_beers: bool = False
    ):
        name = getattr(update_data, "name", None)
        return _Brand(id=beer_brand_id, name=name, beers=[] if load_beers else None)

    monkeypatch.setattr(beer_brand_router, "update_beer_brand", mock_update_brand)

    resp = client.patch("/beer_brands/1/", json={"name": "NewName"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == 1
    assert body["name"] == "NewName"


def test_update_beer_brand_not_found(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_update_brand(
        db, beer_brand_id: int, update_data, *, load_beers: bool = False
    ):
        return None

    monkeypatch.setattr(beer_brand_router, "update_beer_brand", mock_update_brand)

    resp = client.patch("/beer_brands/9999/", json={"name": "Whatever"})
    assert resp.status_code == 404


def test_delete_beer_brand_success(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_delete(db, beer_brand_id: int):
        return True

    monkeypatch.setattr(beer_brand_router, "delete_beer_brand", mock_delete)

    resp = client.delete("/beer_brands/1/")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("success") is True


def test_delete_beer_brand_not_found(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_delete(db, beer_brand_id: int):
        return False

    monkeypatch.setattr(beer_brand_router, "delete_beer_brand", mock_delete)

    resp = client.delete("/beer_brands/9999/")
    assert resp.status_code == 404
