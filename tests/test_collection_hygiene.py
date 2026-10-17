"""Keeping the collection free of duplicates: name cleanup, case-insensitive
reuse, merges, counts and photo replacement. Real Postgres, mocked storage."""

import io
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from PIL import Image
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.auth import verify_admin
from src.api.dependencies.db import get_db_session
from src.api.dependencies.facades import get_beer_cap_facade
from src.api.error_handlers import register_error_handlers
from src.api.routers.beer_brand_router import router as beer_brand_router
from src.api.routers.beer_cap_router import router as beer_cap_router
from src.api.routers.beer_router import router as beer_router
from src.api.routers.country_router import router as country_router
from src.api.schemas.beer_brand.beer_brand_create import BeerBrandCreateSchema
from src.api.schemas.beer_cap.beer_cap_create import BeerCapCreateSchema
from src.api.schemas.country.country_create import CountryCreateSchema
from src.db.crud.augmented_cap_crud import create_augmented_cap
from src.db.crud.beer_brand_crud import create_beer_brand
from src.db.crud.beer_cap_crud import get_beer_cap_by_id
from src.db.crud.beer_crud import create_beer
from src.db.crud.country_crud import create_country
from src.db.entities.beer_brand_entity import BeerBrand
from src.db.entities.beer_cap_entity import BeerCap
from src.db.entities.beer_entity import Beer
from src.services.beer_cap_facade import BeerCapFacade


def _jpeg(color: str = "red") -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (20, 20), color).save(out, format="JPEG")
    return out.getvalue()


def _facade(session: AsyncSession, minio: MagicMock) -> BeerCapFacade:
    @asynccontextmanager
    async def session_maker():
        yield session

    facade = BeerCapFacade(minio_wrapper=minio, session_maker=session_maker)
    facade.original_caps_bucket = "caps"
    facade.augmented_caps_bucket = "augmented"
    return facade


@pytest.fixture
def minio() -> MagicMock:
    mock = MagicMock()
    mock.public_url.side_effect = lambda bucket, key: f"http://img/{key}"
    mock.generate_presigned_url.side_effect = lambda bucket, key: f"http://img/{key}"
    return mock


@pytest.fixture
async def api(
    db_session: AsyncSession, minio: MagicMock
) -> AsyncGenerator[AsyncClient, None]:
    app = FastAPI()
    register_error_handlers(app)
    for router in (beer_cap_router, beer_router, beer_brand_router, country_router):
        app.include_router(router)

    async def session_override():
        yield db_session

    facade = _facade(db_session, minio)
    app.dependency_overrides[get_db_session] = session_override
    app.dependency_overrides[verify_admin] = lambda: None
    app.dependency_overrides[get_beer_cap_facade] = lambda: facade

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def _count(session: AsyncSession, entity: type) -> int:
    return (
        await session.execute(select(func.count()).select_from(entity))
    ).scalar_one()


async def _add_cap(api: AsyncClient, **data: str) -> dict:
    resp = await api.post(
        "/beer_caps/",
        files={"file": ("cap.jpg", _jpeg(), "image/jpeg")},
        data=data,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# --- name cleanup -----------------------------------------------------------


def test_names_are_trimmed_and_inner_spaces_collapsed() -> None:
    assert BeerBrandCreateSchema(name="  Bernard \t  Černý ").name == "Bernard Černý"
    assert CountryCreateSchema(name=" Česká  Republika").name == "Česká Republika"


def test_blank_new_beer_name_is_rejected() -> None:
    with pytest.raises(ValidationError):
        BeerCapCreateSchema(
            filename="cap.jpg", beer_name="   ", beer_brand_id=1, country_id=1
        )


# --- no duplicates ----------------------------------------------------------


async def test_brand_differing_only_in_case_is_409(api: AsyncClient) -> None:
    assert (
        await api.post("/beer_brands/", json={"name": "Bernard"})
    ).status_code == 201

    resp = await api.post("/beer_brands/", json={"name": " bernard "})

    assert resp.status_code == 409


async def test_country_differing_only_in_case_is_409(api: AsyncClient) -> None:
    first = await api.post("/countries/", json={"name": "Česká Republika"})
    assert first.status_code == 201

    resp = await api.post("/countries/", json={"name": "česká republika"})

    assert resp.status_code == 409


async def test_same_beer_name_for_same_brand_is_409(
    api: AsyncClient, db_session: AsyncSession
) -> None:
    brand = await create_beer_brand(db_session, "Gambrinus")
    await create_beer(db_session, "Gambrinus 10°", brand.id)

    resp = await api.post(
        "/beers/", json={"name": "GAMBRINUS  10°", "beer_brand_id": brand.id}
    )

    assert resp.status_code == 409


async def test_same_beer_name_for_another_brand_is_allowed(
    api: AsyncClient, db_session: AsyncSession
) -> None:
    first = await create_beer_brand(db_session, "Pivovar A")
    second = await create_beer_brand(db_session, "Pivovar B")
    await create_beer(db_session, "Ležák", first.id)

    resp = await api.post("/beers/", json={"name": "Ležák", "beer_brand_id": second.id})

    assert resp.status_code == 201


async def test_new_cap_reuses_existing_beer_brand_and_country(
    api: AsyncClient, db_session: AsyncSession
) -> None:
    country = await create_country(db_session, CountryCreateSchema(name="Česko"))
    brand = await create_beer_brand(db_session, "Gambrinus")
    beer = await create_beer(
        db_session, "Gambrinus 10°", brand.id, country_id=country.id
    )

    cap = await _add_cap(
        api,
        beer_name=" gambrinus 10° ",
        beer_brand_name="GAMBRINUS",
        country_name="česko",
    )

    assert cap["beer"]["id"] == beer.id
    assert await _count(db_session, Beer) == 1
    assert await _count(db_session, BeerBrand) == 1


async def test_new_cap_with_new_names_stores_them_cleaned(
    api: AsyncClient, db_session: AsyncSession
) -> None:
    cap = await _add_cap(
        api,
        beer_name="  Nový   ležák ",
        beer_brand_name=" Pivovar  Nový ",
        country_name=" Česko ",
    )

    assert cap["beer"]["name"] == "Nový ležák"
    assert cap["beer"]["beer_brand"]["name"] == "Pivovar Nový"
    assert cap["beer"]["country"]["name"] == "Česko"


# --- merges -----------------------------------------------------------------


async def test_merge_beers_moves_caps_and_fills_missing_details(
    api: AsyncClient, db_session: AsyncSession
) -> None:
    country = await create_country(db_session, CountryCreateSchema(name="Česko"))
    brand = await create_beer_brand(db_session, "Bernard")
    target = await create_beer(db_session, "Bernard 12°", brand.id)
    source = await create_beer(
        db_session, "Bernard 12", brand.id, rating=7, country_id=country.id
    )
    target_id, source_id = target.id, source.id
    await _add_cap(api, beer_id=str(target_id))
    await _add_cap(api, beer_id=str(source_id))

    resp = await api.post(f"/beers/{source_id}/merge/", json={"into_id": target_id})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == target_id
    assert body["cap_count"] == 2
    assert body["rating"] == 7
    assert body["country"]["name"] == "Česko"
    assert (await api.get(f"/beers/{source_id}/")).status_code == 404


async def test_merge_beer_into_itself_is_422(
    api: AsyncClient, db_session: AsyncSession
) -> None:
    brand = await create_beer_brand(db_session, "Bernard")
    beer = await create_beer(db_session, "Bernard 12°", brand.id)

    resp = await api.post(f"/beers/{beer.id}/merge/", json={"into_id": beer.id})

    assert resp.status_code == 422


async def test_merge_into_missing_beer_is_404(
    api: AsyncClient, db_session: AsyncSession
) -> None:
    brand = await create_beer_brand(db_session, "Bernard")
    beer = await create_beer(db_session, "Bernard 12°", brand.id)

    resp = await api.post(f"/beers/{beer.id}/merge/", json={"into_id": 9999})

    assert resp.status_code == 404
    assert await _count(db_session, Beer) == 1


async def test_merge_brands_moves_beers_and_joins_same_named_beers(
    api: AsyncClient, db_session: AsyncSession
) -> None:
    target = await create_beer_brand(db_session, "Plzeňský Prazdroj")
    source = await create_beer_brand(db_session, "Prazdroj")
    kept = await create_beer(db_session, "Plzeň", target.id)
    twin = await create_beer(db_session, "plzeň", source.id)
    moved = await create_beer(db_session, "Gambrinus Dry", source.id)
    target_id, source_id = target.id, source.id
    kept_id, twin_id, moved_id = kept.id, twin.id, moved.id
    await _add_cap(api, beer_id=str(kept_id))
    await _add_cap(api, beer_id=str(twin_id))
    await _add_cap(api, beer_id=str(moved_id))

    resp = await api.post(
        f"/beer_brands/{source_id}/merge/", json={"into_id": target_id}
    )

    assert resp.status_code == 200, resp.text
    assert sorted(b["name"] for b in resp.json()["beers"]) == ["Gambrinus Dry", "Plzeň"]
    assert await _count(db_session, BeerBrand) == 1
    caps = (await db_session.execute(select(BeerCap.beer_id))).scalars().all()
    assert sorted(caps) == sorted([kept_id, kept_id, moved_id])


async def test_merge_countries_moves_beers(
    api: AsyncClient, db_session: AsyncSession
) -> None:
    target = await create_country(db_session, CountryCreateSchema(name="Česko"))
    source = await create_country(db_session, CountryCreateSchema(name="ČR"))
    brand = await create_beer_brand(db_session, "Bernard")
    await create_beer(db_session, "Bernard 12°", brand.id, country_id=source.id)
    target_id, source_id = target.id, source.id

    resp = await api.post(f"/countries/{source_id}/merge/", json={"into_id": target_id})

    assert resp.status_code == 200, resp.text
    assert [b["name"] for b in resp.json()["beers"]] == ["Bernard 12°"]
    assert (await api.get(f"/countries/{source_id}/")).status_code == 404


# --- counts -----------------------------------------------------------------


async def test_lists_include_counts(api: AsyncClient, db_session: AsyncSession) -> None:
    country = await create_country(db_session, CountryCreateSchema(name="Česko"))
    await create_country(db_session, CountryCreateSchema(name="Německo"))
    brand = await create_beer_brand(db_session, "Bernard")
    await create_beer_brand(db_session, "Unused")
    beer = await create_beer(db_session, "Bernard 12°", brand.id, country_id=country.id)
    await create_beer(db_session, "Bernard 11°", brand.id)
    await _add_cap(api, beer_id=str(beer.id))
    await _add_cap(api, beer_id=str(beer.id))

    beers = {b["name"]: b["cap_count"] for b in (await api.get("/beers/")).json()}
    brands = {
        b["name"]: b["beer_count"] for b in (await api.get("/beer_brands/")).json()
    }
    countries = {
        c["name"]: c["beer_count"] for c in (await api.get("/countries/")).json()
    }

    assert beers == {"Bernard 12°": 2, "Bernard 11°": 0}
    assert brands == {"Bernard": 2, "Unused": 0}
    assert countries == {"Česko": 1, "Německo": 0}


# --- replacing a photo ------------------------------------------------------


async def test_replace_image_swaps_objects_and_drops_augmented_caps(
    api: AsyncClient, db_session: AsyncSession, minio: MagicMock
) -> None:
    brand = await create_beer_brand(db_session, "Bernard")
    beer = await create_beer(db_session, "Bernard 12°", brand.id)
    cap = await _add_cap(api, beer_id=str(beer.id))
    old = await get_beer_cap_by_id(db_session, cap["id"])
    assert old and old.thumbnail_s3_key
    old_key, old_thumb = old.s3_key, old.thumbnail_s3_key
    await create_augmented_cap(db_session, cap["id"], "aug/1.png")
    minio.reset_mock()

    resp = await api.put(
        f"/beer_caps/{cap['id']}/image/",
        files={"file": ("new.jpg", _jpeg("blue"), "image/jpeg")},
    )

    assert resp.status_code == 200, resp.text
    db_session.expunge_all()
    updated = await get_beer_cap_by_id(db_session, cap["id"], load_augmented_caps=True)
    assert updated
    assert updated.s3_key != old_key
    assert updated.thumbnail_s3_key and updated.thumbnail_s3_key != old_thumb
    assert updated.augmented_caps == []
    assert resp.json()["presigned_url"] == f"http://img/{updated.s3_key}"

    uploaded = [c.args[1] for c in minio.upload_file.call_args_list]
    deleted = [c.args[1] for c in minio.delete_file.call_args_list]
    assert uploaded == [updated.s3_key, updated.thumbnail_s3_key]
    assert sorted(deleted) == sorted(["aug/1.png", old_key, old_thumb])


async def test_replace_image_of_missing_cap_is_404(api: AsyncClient) -> None:
    resp = await api.put(
        "/beer_caps/9999/image/",
        files={"file": ("new.jpg", _jpeg(), "image/jpeg")},
    )

    assert resp.status_code == 404


async def test_replace_image_rejects_non_images(
    api: AsyncClient, db_session: AsyncSession
) -> None:
    brand = await create_beer_brand(db_session, "Bernard")
    beer = await create_beer(db_session, "Bernard 12°", brand.id)
    cap = await _add_cap(api, beer_id=str(beer.id))

    resp = await api.put(
        f"/beer_caps/{cap['id']}/image/",
        files={"file": ("new.jpg", b"not an image", "image/jpeg")},
    )

    assert resp.status_code == 415
