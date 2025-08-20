import importlib
from typing import Optional

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.dependencies.db import get_db_session

country_router = importlib.import_module("src.api.routers.country_router")


@pytest.fixture()
def client() -> TestClient:
    app = FastAPI()
    app.include_router(country_router.router)

    async def override_db():
        yield None

    app.dependency_overrides[get_db_session] = override_db
    return TestClient(app)


class _Country:
    def __init__(
        self,
        id: int,
        name: str,
        description: Optional[str] = None,
        beers: Optional[list] = None,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.beers = beers


def test_create_country_success(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_create_country(db, create_data_or_name, **kwargs):
        if isinstance(create_data_or_name, str):
            name = create_data_or_name
            desc = None
        else:
            name = getattr(create_data_or_name, "name", None)
            desc = getattr(create_data_or_name, "description", None)
        return _Country(id=1, name=name, description=desc, beers=[])

    monkeypatch.setattr(country_router, "create_country", mock_create_country)

    resp = client.post(
        "/countries/", json={"name": "Czech Republic", "description": "Central Europe"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 1
    assert data["name"] == "Czech Republic"
    assert data["description"] == "Central Europe"


def test_list_countries(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def mock_get_all_countries(db, *, load_beers: bool = False, **_):
        return [
            _Country(
                id=1,
                name="Czech Republic",
                description="Central Europe",
                beers=[] if load_beers else None,
            ),
            _Country(
                id=2,
                name="Germany",
                description="Beer country",
                beers=[] if load_beers else None,
            ),
        ]

    monkeypatch.setattr(country_router, "get_all_countries", mock_get_all_countries)

    resp = client.get("/countries/")
    assert resp.status_code == 200
    payload = resp.json()
    assert isinstance(payload, list) and len(payload) == 2
    names = {c["name"] for c in payload}
    assert names == {"Czech Republic", "Germany"}
    assert all("description" in c for c in payload)


def test_get_country_by_id_found(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_get_country_by_id(
        db, country_id: int, *, load_beers: bool = False, **_
    ):
        return _Country(
            id=country_id,
            name="Czech Republic",
            description="Central Europe",
            beers=[] if load_beers else None,
        )

    monkeypatch.setattr(country_router, "get_country_by_id", mock_get_country_by_id)

    resp = client.get("/countries/1/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 1
    assert data["name"] == "Czech Republic"
    assert "description" in data


def test_get_country_by_id_not_found(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_get_country_by_id(
        db, country_id: int, *, load_beers: bool = False, **_
    ):
        return None

    monkeypatch.setattr(country_router, "get_country_by_id", mock_get_country_by_id)

    resp = client.get("/countries/9999/")
    assert resp.status_code == 404


def test_update_country_success(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_update_country(
        db, country_id: int, update_data, *, load_beers: bool = False, **_
    ):
        name = getattr(update_data, "name", None)
        desc = getattr(update_data, "description", None)
        return _Country(
            id=country_id, name=name, description=desc, beers=[] if load_beers else None
        )

    monkeypatch.setattr(country_router, "update_country", mock_update_country)

    resp = client.patch("/countries/1/", json={"name": "Czechia"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == 1
    assert body["name"] == "Czechia"
    assert "description" in body


def test_update_country_not_found(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_update_country(
        db, country_id: int, update_data, *, load_beers: bool = False, **_
    ):
        return None

    monkeypatch.setattr(country_router, "update_country", mock_update_country)

    resp = client.patch("/countries/9999/", json={"name": "Atlantis"})
    assert resp.status_code == 404


def test_create_country_success(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_create_country(*args, **kwargs):
        name = None
        desc = None

        if len(args) >= 2:
            maybe = args[1]
            if isinstance(maybe, str):
                name = maybe
                if len(args) >= 3:
                    desc = args[2]
            else:
                name = getattr(maybe, "name", None)
                desc = getattr(maybe, "description", None)

        if name is None:
            model = kwargs.get("create_data") or kwargs.get("create_data_or_name")
            if model is not None:
                name = getattr(model, "name", None)
                desc = getattr(model, "description", None)

        return _Country(id=1, name=name, description=desc, beers=[])

    monkeypatch.setattr(country_router, "create_country", mock_create_country)

    resp = client.post(
        "/countries/",
        data={"name": "Czech Republic", "description": "Central Europe"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 1
    assert data["name"] == "Czech Republic"
    assert data["description"] == "Central Europe"


def test_delete_country_not_found(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_get_country_by_id(
        db, country_id: int, *, load_beers: bool = False, **_
    ):
        return None

    async def mock_delete_country(db, country_id: int):
        return False

    monkeypatch.setattr(country_router, "get_country_by_id", mock_get_country_by_id)
    monkeypatch.setattr(country_router, "delete_country", mock_delete_country)

    resp = client.delete("/countries/9999/")
    assert resp.status_code == 404
