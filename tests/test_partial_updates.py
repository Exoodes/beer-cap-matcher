"""PATCH semantics (omit = keep, null = clear) and JSON creates, on a real DB."""

from collections.abc import AsyncGenerator
from datetime import date
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.auth import verify_admin
from src.api.dependencies.db import get_db_session
from src.api.dependencies.facades import get_beer_cap_facade
from src.api.error_handlers import register_error_handlers
from src.api.routers.beer_cap_router import router as beer_cap_router
from src.api.routers.beer_router import router as beer_router
from src.api.routers.country_router import router as country_router
from src.api.schemas.beer_cap.beer_cap_create import BeerCapCreateSchema
from src.api.schemas.country.country_create import CountryCreateSchema
from src.db.crud.beer_brand_crud import create_beer_brand
from src.db.crud.beer_cap_crud import create_beer_cap, get_beer_cap_by_id
from src.db.crud.beer_crud import create_beer, get_beer_by_id
from src.db.crud.country_crud import create_country


@pytest.fixture
async def api(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    app = FastAPI()
    register_error_handlers(app)
    for router in (beer_router, beer_cap_router, country_router):
        app.include_router(router)

    async def session_override():
        yield db_session

    facade = MagicMock()
    facade.get_image_url.return_value = "http://x/cap.jpg"
    app.dependency_overrides[get_db_session] = session_override
    app.dependency_overrides[verify_admin] = lambda: None
    app.dependency_overrides[get_beer_cap_facade] = lambda: facade

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def beer(db_session: AsyncSession) -> dict[str, int]:
    country = await create_country(db_session, CountryCreateSchema(name="CZ"))
    brand = await create_beer_brand(db_session, "Brand")
    beer = await create_beer(db_session, "Lager", brand.id, country_id=country.id)
    cap = await create_beer_cap(
        db_session,
        beer.id,
        "caps/x.jpg",
        BeerCapCreateSchema(
            filename="x.jpg", variant_name="Gold", collected_date=date(2024, 5, 1)
        ),
    )
    return {"beer": beer.id, "cap": cap.id, "brand": brand.id, "country": country.id}


async def _reload_cap(session: AsyncSession, cap_id: int):
    session.expunge_all()
    return await get_beer_cap_by_id(session, cap_id)


async def _reload_beer(session: AsyncSession, beer_id: int):
    session.expunge_all()
    return await get_beer_by_id(session, beer_id)


async def test_null_clears_cap_date_and_omitted_fields_are_kept(
    api: AsyncClient, db_session: AsyncSession, beer: dict[str, int]
) -> None:
    resp = await api.patch(f"/beer_caps/{beer['cap']}/", json={"collected_date": None})

    assert resp.status_code == 200
    cap = await _reload_cap(db_session, beer["cap"])
    assert cap is not None
    assert cap.collected_date is None
    assert cap.variant_name == "Gold"


async def test_null_clears_beer_country(
    api: AsyncClient, db_session: AsyncSession, beer: dict[str, int]
) -> None:
    resp = await api.patch(f"/beers/{beer['beer']}/", json={"country_id": None})

    assert resp.status_code == 200
    reloaded = await _reload_beer(db_session, beer["beer"])
    assert reloaded is not None
    assert reloaded.country_id is None
    assert reloaded.name == "Lager"


@pytest.mark.parametrize(
    "body",
    [{"beer_brand_id": None}, {"name": None}, {"rating": None}],
)
async def test_null_is_rejected_for_required_beer_fields(
    api: AsyncClient, beer: dict[str, int], body: dict
) -> None:
    resp = await api.patch(f"/beers/{beer['beer']}/", json=body)

    assert resp.status_code == 422
    assert "cannot be null" in resp.json()["detail"][0]["msg"]


async def test_null_is_rejected_for_cap_beer_id(
    api: AsyncClient, beer: dict[str, int]
) -> None:
    resp = await api.patch(f"/beer_caps/{beer['cap']}/", json={"beer_id": None})

    assert resp.status_code == 422


async def test_unknown_brand_reference_is_409(
    api: AsyncClient, beer: dict[str, int]
) -> None:
    resp = await api.patch(f"/beers/{beer['beer']}/", json={"beer_brand_id": 999})

    assert resp.status_code == 409
    assert "does not exist" in resp.json()["detail"]


@pytest.mark.parametrize(
    "body", [{"name": "Slovakia"}, {"name": "Slovakia", "description": ""}]
)
async def test_country_create_accepts_json_with_optional_description(
    api: AsyncClient, body: dict
) -> None:
    resp = await api.post("/countries/", json=body)

    assert resp.status_code == 201
    assert resp.json()["name"] == "Slovakia"


async def test_delete_returns_204(api: AsyncClient, db_session: AsyncSession) -> None:
    country = await create_country(db_session, CountryCreateSchema(name="Unused"))

    resp = await api.delete(f"/countries/{country.id}/")

    assert resp.status_code == 204
    assert resp.content == b""
