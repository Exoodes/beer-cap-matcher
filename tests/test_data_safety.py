"""Uploads, DB/storage ordering and error mapping, against real Postgres/MinIO."""

import io
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from httpx import ASGITransport, AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.auth import verify_admin
from src.api.dependencies.db import get_db_session
from src.api.dependencies.facades import get_beer_cap_facade
from src.api.error_handlers import register_error_handlers
from src.api.routers.beer_brand_router import router as beer_brand_router
from src.api.routers.beer_cap_router import router as beer_cap_router
from src.api.routers.country_router import router as country_router
from src.api.schemas.beer_cap.beer_cap_create import BeerCapCreateSchema
from src.api.schemas.country.country_create import CountryCreateSchema
from src.config import settings
from src.db.crud.beer_brand_crud import create_beer_brand
from src.db.crud.beer_cap_crud import get_all_beer_caps, get_beer_cap_by_id
from src.db.crud.beer_crud import create_beer, get_beer_by_id
from src.db.crud.country_crud import create_country
from src.services.beer_cap_facade import BeerCapFacade
from src.storage.minio.minio_client import MinioClientWrapper
from src.utils.image_ingest import InvalidImageError, normalize_image
from tests.conftest import TEST_BUCKET_NAME


def _jpeg(size: tuple[int, int], color: str = "red", **save_kwargs) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", size, color).save(out, format="JPEG", **save_kwargs)
    return out.getvalue()


# --- normalize_image -------------------------------------------------------


def test_normalize_downscales_and_reencodes_as_jpeg() -> None:
    png = io.BytesIO()
    Image.new("RGBA", (4000, 1000), (0, 0, 255, 128)).save(png, format="PNG")

    result = Image.open(io.BytesIO(normalize_image(png.getvalue(), max_side=2048)))

    assert result.format == "JPEG"
    assert result.size == (2048, 512)


def test_normalize_applies_exif_rotation() -> None:
    exif = Image.Exif()
    exif[0x0112] = 6  # Orientation: rotate 90° clockwise to display
    data = _jpeg((300, 100), exif=exif.tobytes())

    result = Image.open(io.BytesIO(normalize_image(data, max_side=2048)))

    assert result.size == (100, 300)


@pytest.mark.parametrize("data", [b"hello", b"\xff\xd8\xff\x00", b""])
def test_normalize_rejects_non_images(data: bytes) -> None:
    with pytest.raises(InvalidImageError):
        normalize_image(data, max_side=2048)


# --- facade ordering --------------------------------------------------------


def _facade(session: AsyncSession, minio: MinioClientWrapper) -> BeerCapFacade:
    @asynccontextmanager
    async def session_maker():
        yield session

    facade = BeerCapFacade(minio_wrapper=minio, session_maker=session_maker)
    facade.original_caps_bucket = TEST_BUCKET_NAME
    facade.augmented_caps_bucket = TEST_BUCKET_NAME
    return facade


async def _beer_id(session: AsyncSession) -> int:
    brand = await create_beer_brand(session, "Brand")
    beer = await create_beer(session, "Beer", brand.id)
    return beer.id


async def test_same_client_filename_never_overwrites_another_cap(
    db_session: AsyncSession, real_minio_client: MinioClientWrapper
) -> None:
    facade = _facade(db_session, real_minio_client)
    beer_id = await _beer_id(db_session)
    first, second = _jpeg((10, 10), "red"), _jpeg((10, 10), "blue")

    caps = []
    for data in (first, second):
        caps.append(
            await facade.create_cap_for_existing_beer_and_upload(
                beer_id,
                BeerCapCreateSchema(filename="image.jpg"),
                io.BytesIO(data),
                len(data),
                content_type="image/jpeg",
            )
        )

    assert caps[0] and caps[1]
    assert caps[0].s3_key != caps[1].s3_key
    stored = [
        real_minio_client.download_bytes(TEST_BUCKET_NAME, c.s3_key) for c in caps
    ]
    assert stored == [first, second]


async def test_failed_upload_leaves_no_cap_row(
    db_session: AsyncSession, mock_minio_client_wrapper: MagicMock
) -> None:
    facade = _facade(db_session, mock_minio_client_wrapper)
    beer_id = await _beer_id(db_session)
    mock_minio_client_wrapper.upload_file.side_effect = ConnectionError("down")

    with pytest.raises(ConnectionError):
        await facade.create_cap_for_existing_beer_and_upload(
            beer_id,
            BeerCapCreateSchema(filename="cap.jpg"),
            io.BytesIO(b"x"),
            1,
            content_type="image/jpeg",
        )
    await db_session.rollback()

    assert await get_all_beer_caps(db_session) == []


async def test_failed_commit_removes_uploaded_object(
    db_session: AsyncSession, mock_minio_client_wrapper: MagicMock
) -> None:
    facade = _facade(db_session, mock_minio_client_wrapper)
    beer_id = await _beer_id(db_session)
    db_session.commit = AsyncMock(side_effect=RuntimeError("commit failed"))  # type: ignore[method-assign]

    with pytest.raises(RuntimeError):
        await facade.create_cap_for_existing_beer_and_upload(
            beer_id,
            BeerCapCreateSchema(filename="cap.jpg"),
            io.BytesIO(b"x"),
            1,
            content_type="image/jpeg",
        )

    uploaded_key = mock_minio_client_wrapper.upload_file.call_args.args[1]
    mock_minio_client_wrapper.delete_file.assert_called_once_with(
        TEST_BUCKET_NAME, uploaded_key
    )


async def test_delete_succeeds_even_if_storage_delete_fails(
    db_session: AsyncSession, mock_minio_client_wrapper: MagicMock
) -> None:
    facade = _facade(db_session, mock_minio_client_wrapper)
    beer_id = await _beer_id(db_session)
    cap = await facade.create_cap_for_existing_beer_and_upload(
        beer_id,
        BeerCapCreateSchema(filename="cap.jpg"),
        io.BytesIO(b"x"),
        1,
        content_type="image/jpeg",
    )
    assert cap
    mock_minio_client_wrapper.delete_file.side_effect = ConnectionError("down")

    assert await facade.delete_beer_cap_and_its_augmented_caps(cap.id) is True
    assert await get_beer_cap_by_id(db_session, cap.id) is None


# --- HTTP error mapping -----------------------------------------------------


@pytest.fixture
async def api(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    app = FastAPI()
    register_error_handlers(app)
    app.add_middleware(
        CORSMiddleware, allow_origins=[settings.frontend_url], allow_methods=["*"]
    )
    for router in (beer_cap_router, beer_brand_router, country_router):
        app.include_router(router)

    async def session_override():
        yield db_session

    app.dependency_overrides[get_db_session] = session_override
    app.dependency_overrides[verify_admin] = lambda: None
    app.dependency_overrides[get_beer_cap_facade] = lambda: MagicMock()

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("unexpected")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.app = app  # type: ignore[attr-defined]
        yield client


async def test_duplicate_country_is_409(api: AsyncClient) -> None:
    data = {"name": "Czechia", "description": "x"}
    assert (await api.post("/countries/", data=data)).status_code == 200

    resp = await api.post("/countries/", data=data)

    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]


async def test_duplicate_brand_is_409(api: AsyncClient) -> None:
    assert (
        await api.post("/beer_brands/", data={"name": "Bernard"})
    ).status_code == 200

    resp = await api.post("/beer_brands/", data={"name": "Bernard"})

    assert resp.status_code == 409


async def test_deleting_brand_still_used_by_beers_is_409(
    api: AsyncClient, db_session: AsyncSession
) -> None:
    brand = await create_beer_brand(db_session, "Used")
    await create_beer(db_session, "Beer", brand.id)

    resp = await api.delete(f"/beer_brands/{brand.id}/")

    assert resp.status_code == 409
    assert "still used" in resp.json()["detail"]


async def test_deleting_country_still_used_by_beers_is_409(
    api: AsyncClient, db_session: AsyncSession
) -> None:
    country = await create_country(db_session, CountryCreateSchema(name="CZ"))
    brand = await create_beer_brand(db_session, "Brand")
    beer = await create_beer(db_session, "Beer", brand.id, country_id=country.id)
    beer_id, country_id = beer.id, country.id

    resp = await api.delete(f"/countries/{country_id}/")

    assert resp.status_code == 409
    await db_session.rollback()  # the test shares the request's session
    reloaded = await get_beer_by_id(db_session, beer_id)
    assert reloaded is not None and reloaded.country_id == country_id


async def test_unknown_brand_id_on_create_is_404(
    api: AsyncClient, dummy_image_bytes: bytes
) -> None:
    facade = BeerCapFacade(minio_wrapper=MagicMock())
    api.app.dependency_overrides[get_beer_cap_facade] = lambda: facade  # type: ignore[attr-defined]

    resp = await api.post(
        "/beer_caps/",
        files={"file": ("cap.jpg", dummy_image_bytes, "image/jpeg")},
        data={"beer_name": "New", "beer_brand_id": "999", "country_name": "CZ"},
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Beer brand not found."


async def test_new_beer_without_country_is_422(
    api: AsyncClient, dummy_image_bytes: bytes
) -> None:
    resp = await api.post(
        "/beer_caps/",
        files={"file": ("cap.jpg", dummy_image_bytes, "image/jpeg")},
        data={"beer_name": "New", "beer_brand_name": "Brand"},
    )

    assert resp.status_code == 422
    assert "country" in resp.json()["detail"][0]["msg"]


async def test_corrupt_upload_is_415(api: AsyncClient) -> None:
    resp = await api.post(
        "/beer_caps/",
        files={"file": ("cap.heic", b"not really an image", "image/heic")},
        data={"beer_id": "1"},
    )
    assert resp.status_code == 415


async def test_oversized_upload_is_413(
    api: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "max_upload_bytes", 100)
    resp = await api.post(
        "/beer_caps/",
        files={"file": ("cap.jpg", _jpeg((200, 200)), "image/jpeg")},
        data={"beer_id": "1"},
    )
    assert resp.status_code == 413


async def test_unhandled_error_is_json_500_with_cors_headers(api: AsyncClient) -> None:
    resp = await api.get("/boom", headers={"Origin": settings.frontend_url})

    assert resp.status_code == 500
    assert resp.json() == {"detail": "Internal server error."}
    assert resp.headers["access-control-allow-origin"] == settings.frontend_url


async def test_caps_by_beer_loads_brand_and_country(
    api: AsyncClient, db_session: AsyncSession
) -> None:
    facade = MagicMock()
    facade.get_presigned_url_for_cap.return_value = "http://x/cap.jpg"
    api.app.dependency_overrides[get_beer_cap_facade] = lambda: facade  # type: ignore[attr-defined]
    beer_id = await _beer_id(db_session)
    empty = await api.get(f"/beer_caps/by-beer/{beer_id}/")

    real_facade = _facade(db_session, MagicMock())
    await real_facade.create_cap_for_existing_beer_and_upload(
        beer_id,
        BeerCapCreateSchema(filename="cap.jpg"),
        io.BytesIO(b"x"),
        1,
        content_type="image/jpeg",
    )
    db_session.expunge_all()  # force a fresh load, as in a new request
    resp = await api.get(f"/beer_caps/by-beer/{beer_id}/")

    assert empty.status_code == 200 and empty.json() == []
    assert resp.status_code == 200
    assert resp.json()[0]["beer"]["beer_brand"]["name"] == "Brand"
