import importlib
from typing import Optional

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.dependencies.db import get_db_session
from src.api.dependencies.facades import get_beer_cap_facade

beer_router = importlib.import_module("src.api.routers.beer_router")


@pytest.fixture()
def client() -> TestClient:
    app = FastAPI()
    app.include_router(beer_router.router)

    async def override_db():
        yield None

    app.dependency_overrides[get_db_session] = override_db

    class _FacadeStub:
        async def delete_beer_and_caps(self, beer_id: int) -> bool:
            raise RuntimeError("Facade not overridden in this test")

    app.dependency_overrides[get_beer_cap_facade] = lambda: _FacadeStub()

    return TestClient(app)


class _Beer:
    def __init__(
        self,
        id: int,
        name: str,
        rating: Optional[int] = None,
        brand: Optional[dict] = None,
        country: Optional[dict] = None,
        caps: Optional[list] = None,
    ):
        self.id = id
        self.name = name
        self.rating = rating
        self.brand = brand
        self.country = country
        self.caps = caps


def test_create_beer_success(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_create_beer(**kwargs):
        name = kwargs.get("name")
        rating = kwargs.get("rating")
        beer_brand_id = kwargs.get("beer_brand_id")
        country_id = kwargs.get("country_id")

        brand = (
            {"id": beer_brand_id, "name": "BrandX"}
            if beer_brand_id is not None
            else None
        )
        country = (
            {"id": country_id, "name": "CountryX"} if country_id is not None else None
        )
        return _Beer(
            id=1, name=name or "BeerX", rating=rating, brand=brand, country=country
        )

    monkeypatch.setattr(beer_router, "create_beer", mock_create_beer)

    resp = client.post(
        "/beers/",
        json={
            "name": "Lager",
            "rating": 4,
            "beer_brand_id": 10,
            "country_id": 20,
        },
    )
    assert resp.status_code == 200


def test_list_beers(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def mock_get_all_beers(
        db, *, load_caps: bool = False, load_country: bool = False, **_
    ):
        caps = (
            [{"id": 100, "variant_name": "CapA", "collected_date": None}]
            if load_caps
            else None
        )
        country = (
            {"id": 20, "name": "CountryA", "description": "Desc"}
            if load_country
            else None
        )
        return [
            _Beer(id=1, name="Lager", rating=4, caps=caps, country=country),
            _Beer(id=2, name="Stout", rating=3, caps=caps, country=country),
        ]

    monkeypatch.setattr(beer_router, "get_all_beers", mock_get_all_beers)

    resp = client.get("/beers/")
    assert resp.status_code == 200
    payload = resp.json()
    assert isinstance(payload, list) and len(payload) == 2
    names = {b["name"] for b in payload}
    assert names == {"Lager", "Stout"}


def test_get_beer_by_id_found(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_get_beer_by_id(
        db, beer_id: int, *, load_caps: bool = False, load_country: bool = False, **_
    ):
        caps = (
            [{"id": 100, "variant_name": "CapA", "collected_date": None}]
            if load_caps
            else None
        )
        country = (
            {"id": 20, "name": "CountryA", "description": "Desc"}
            if load_country
            else None
        )
        return _Beer(id=beer_id, name="Lager", rating=4, caps=caps, country=country)

    monkeypatch.setattr(beer_router, "get_beer_by_id", mock_get_beer_by_id)

    resp = client.get("/beers/1/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 1
    assert data["name"] == "Lager"


def test_get_beer_by_id_not_found(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_get_beer_by_id(db, beer_id: int, **_):
        return None

    monkeypatch.setattr(beer_router, "get_beer_by_id", mock_get_beer_by_id)

    resp = client.get("/beers/9999/")
    assert resp.status_code == 404


def test_update_beer_success(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_update_beer(
        db,
        beer_id: int,
        update_data,
        *,
        load_caps: bool = False,
        load_country: bool = False,
        **_
    ):
        name = getattr(update_data, "name", None)
        rating = getattr(update_data, "rating", None)
        return _Beer(
            id=beer_id, name=name or "Updated", rating=rating, caps=[], country=None
        )

    monkeypatch.setattr(beer_router, "update_beer", mock_update_beer)

    resp = client.patch("/beers/1/?beer_cap_id=1", json={"name": "UpdatedLager"})
    assert resp.status_code == 200


def test_update_beer_not_found(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_update_beer(db, beer_id: int, update_data, **_):
        return None

    monkeypatch.setattr(beer_router, "update_beer", mock_update_beer)

    resp = client.patch("/beers/9999/?beer_cap_id=9999", json={"name": "Whatever"})
    assert resp.status_code == 404


def test_delete_beer_success(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _FacadeOK:
        async def delete_beer_and_caps(self, beer_id: int) -> bool:
            return True

    client.app.dependency_overrides[get_beer_cap_facade] = lambda: _FacadeOK()

    resp = client.delete("/beers/1/")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("success") is True or payload.get("id") == 1


def test_delete_beer_not_found(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _FacadeNotFound:
        async def delete_beer_and_caps(self, beer_id: int) -> bool:
            return False

    client.app.dependency_overrides[get_beer_cap_facade] = lambda: _FacadeNotFound()

    resp = client.delete("/beers/9999/")
    assert resp.status_code == 404
