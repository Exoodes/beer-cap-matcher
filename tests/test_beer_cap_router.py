import importlib
import io
from datetime import date
from typing import Optional, cast

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

beer_cap_router = importlib.import_module("src.api.routers.beer_cap_router")


class _Beer:
    def __init__(self, id: int, name: str, rating: Optional[float] = None):
        self.id = id
        self.name = name
        self.rating = rating


class _BeerCap:
    def __init__(
        self,
        id: int,
        filename: str = "cap.jpg",
        variant_name: Optional[str] = None,
        collected_date: Optional[date] = None,
        beer: Optional[_Beer] = None,
        storage_key: str = "caps/cap.jpg",
    ):
        self.id = id
        self.filename = filename
        self.variant_name = variant_name
        self.collected_date = collected_date
        self.beer = beer or _Beer(1, "Lager", rating=4.0)
        self.beer_id = self.beer.id
        self.s3_key = storage_key


class _DummyFacade:
    def __init__(self):
        self._delete_ok = True

    async def create_cap_and_related_entities(
        self, cap_metadata, image_data, image_length, content_type
    ):
        return _BeerCap(
            id=1,
            filename=cap_metadata.filename,
            variant_name=cap_metadata.variant_name,
            collected_date=cap_metadata.collected_date,
            beer=_Beer(1, cap_metadata.beer_name or "BeerX", rating=4.0),
            storage_key="caps/1.jpg",
        )

    def get_presigned_url_for_cap(self, storage_key: str) -> str:
        return f"https://example.test/{storage_key}"

    async def delete_beer_cap_and_its_augmented_caps(self, beer_cap_id: int) -> bool:
        return self._delete_ok


@pytest.fixture
def client(db_session):
    from src.api.dependencies.db import get_db_session
    from src.api.dependencies.facades import get_beer_cap_facade

    app = FastAPI()
    app.include_router(beer_cap_router.router)

    dummy = _DummyFacade()
    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_beer_cap_facade] = lambda: dummy

    with TestClient(app) as c:
        yield c


def test_create_cap_success(client: TestClient) -> None:
    files = {"file": ("cap.jpg", b"\xff\xd8\xff\x00", "image/jpeg")}
    data = {
        "variant_name": "Gold Rim",
        "beer_name": "Test Beer",
        "beer_brand_id": "10",
        "beer_brand_name": "BrandX",
    }
    resp = client.post("/beer_caps/", files=files, data=data)
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == 1
    assert body["beer"]["name"] in ("Test Beer", "BeerX")
    assert body["presigned_url"].startswith("https://")


def test_create_cap_invalid_file_type(client: TestClient) -> None:
    files = {"file": ("not-image.txt", b"hello", "text/plain")}
    resp = client.post("/beer_caps/", files=files, data={})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid file type. Only images are allowed."


def test_list_caps(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def mock_get_all(db, load_beer: bool = True):
        return [_BeerCap(id=1, variant_name="A"), _BeerCap(id=2, variant_name="B")]

    monkeypatch.setattr(beer_cap_router, "get_all_beer_caps", mock_get_all)

    resp = client.get("/beer_caps/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


def test_get_caps_by_beer_found(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_get_by_beer(db, beer_id: int, load_beer: bool = True):
        return [_BeerCap(id=5, beer=_Beer(123, "Found", rating=4.0))]

    monkeypatch.setattr(beer_cap_router, "get_beer_caps_by_beer_id", mock_get_by_beer)
    resp = client.get("/beer_caps/by-beer/123/")
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["beer"]["id"] == 123


def test_get_caps_by_beer_not_found(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_get_by_beer(db, beer_id: int, load_beer: bool = True):
        return []

    monkeypatch.setattr(beer_cap_router, "get_beer_caps_by_beer_id", mock_get_by_beer)
    resp = client.get("/beer_caps/by-beer/999/")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "No beer caps found for this beer."


def test_get_cap_by_id_found(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_get_by_id(db, cap_id: int, load_beer: bool = True):
        return _BeerCap(id=42, beer=_Beer(9, "X", rating=4.0))

    monkeypatch.setattr(beer_cap_router, "get_beer_cap_by_id", mock_get_by_id)
    resp = client.get("/beer_caps/42/")
    assert resp.status_code == 200
    assert resp.json()["id"] == 42


def test_get_cap_by_id_not_found(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_get_by_id(db, cap_id: int, load_beer: bool = True):
        return None

    monkeypatch.setattr(beer_cap_router, "get_beer_cap_by_id", mock_get_by_id)
    resp = client.get("/beer_caps/404/")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Beer cap not found."


def test_update_cap_success(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_update(db, cap_id: int, update_data, load_beer: bool = True):
        return _BeerCap(id=7, variant_name=update_data.variant_name)

    monkeypatch.setattr(beer_cap_router, "update_beer_cap", mock_update)
    resp = client.patch("/beer_caps/7/", json={"variant_name": "New Variant"})
    assert resp.status_code == 200
    assert resp.json()["variant_name"] == "New Variant"


def test_update_cap_not_found(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def mock_update(db, cap_id: int, update_data, load_beer: bool = True):
        return None

    monkeypatch.setattr(beer_cap_router, "update_beer_cap", mock_update)
    resp = client.patch("/beer_caps/8888/", json={"variant_name": "X"})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Beer cap not found."


def test_delete_cap_success(client: TestClient) -> None:
    resp = client.delete("/beer_caps/9/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True


def test_delete_cap_not_found(client: TestClient) -> None:
    from src.api.dependencies.facades import get_beer_cap_facade

    app = client.app
    not_found = _DummyFacade()
    not_found._delete_ok = False
    app.dependency_overrides[get_beer_cap_facade] = lambda: not_found
    try:
        resp = client.delete("/beer_caps/404/")
    finally:
        app.dependency_overrides.pop(get_beer_cap_facade, None)

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Beer cap not found."
