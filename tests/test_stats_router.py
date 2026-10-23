import importlib
from datetime import date

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from src.db.crud.stats_crud import CollectionStats

stats_router = importlib.import_module("src.api.routers.stats_router")


class _Beer:
    name = "Kozel 11"


class _Cap:
    def __init__(self, id: int, thumbnail: str | None):
        self.id = id
        self.s3_key = f"caps/{id}.jpg"
        self.thumbnail_s3_key = thumbnail
        self.beer = _Beer()


class _Facade:
    def get_image_url(self, key: str) -> str:
        return f"https://files.test/{key}"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    from src.api.dependencies.db import get_db_session
    from src.api.dependencies.facades import get_beer_cap_facade

    seen: dict[str, date] = {}

    async def fake_stats(db, today: date) -> CollectionStats:
        seen["today"] = today
        return CollectionStats(
            caps=3,
            beers=2,
            brands=1,
            countries=1,
            collected_this_month=1,
            growth=[("2026-09", 2), ("2026-10", 3)],
            undated=0,
            newest=[_Cap(3, "thumbs/3.webp"), _Cap(2, None)],
            cap_ids=[1, 2, 3],
        )

    monkeypatch.setattr(stats_router, "get_collection_stats", fake_stats)
    monkeypatch.setattr(stats_router, "today_local", lambda: date(2026, 10, 23))
    app = FastAPI()
    app.include_router(stats_router.router)
    app.dependency_overrides[get_db_session] = lambda: None
    app.dependency_overrides[get_beer_cap_facade] = lambda: _Facade()
    with TestClient(app) as c:
        c.seen = seen  # type: ignore[attr-defined]
        yield c


def test_stats_shape(client: TestClient) -> None:
    resp = client.get("/stats/")
    assert resp.status_code == 200
    assert resp.json() == {
        "caps": 3,
        "beers": 2,
        "brands": 1,
        "countries": 1,
        "collected_this_month": 1,
        "growth": [
            {"month": "2026-09", "total": 2},
            {"month": "2026-10", "total": 3},
        ],
        "undated": 0,
        "newest": [
            {
                "id": 3,
                "beer": "Kozel 11",
                "thumbnail_url": "https://files.test/thumbs/3.webp",
            },
            # No thumbnail yet: the full image.
            {
                "id": 2,
                "beer": "Kozel 11",
                "thumbnail_url": "https://files.test/caps/2.jpg",
            },
        ],
        "cap_ids": [1, 2, 3],
    }
    # "This month" is Prague's.
    assert client.seen["today"] == date(2026, 10, 23)  # type: ignore[attr-defined]
