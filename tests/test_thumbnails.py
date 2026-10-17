"""Thumbnails and stable image URLs, against real Postgres/MinIO."""

import io
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.beer_cap.beer_cap_create import BeerCapCreateSchema
from src.api.utils import build_beer_cap_response
from src.db.crud.beer_brand_crud import create_beer_brand
from src.db.crud.beer_cap_crud import create_beer_cap, get_beer_cap_by_id
from src.db.crud.beer_crud import create_beer
from src.services.beer_cap_facade import (
    IMMUTABLE_CACHE_CONTROL,
    BeerCapFacade,
    thumbnail_object_name,
)
from src.storage.minio.minio_client import MinioClientWrapper
from src.utils.image_ingest import InvalidImageError, make_thumbnail
from tests.conftest import TEST_BUCKET_NAME


def _jpeg(size: tuple[int, int], **save_kwargs) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", size, "orange").save(out, format="JPEG", **save_kwargs)
    return out.getvalue()


def _facade(session: AsyncSession, minio) -> BeerCapFacade:
    @asynccontextmanager
    async def session_maker():
        yield session

    facade = BeerCapFacade(minio_wrapper=minio, session_maker=session_maker)
    facade.original_caps_bucket = TEST_BUCKET_NAME
    facade.augmented_caps_bucket = TEST_BUCKET_NAME
    return facade


async def _beer_id(session: AsyncSession) -> int:
    brand = await create_beer_brand(session, "Brand")
    return (await create_beer(session, "Beer", brand.id)).id


# --- make_thumbnail ---------------------------------------------------------


def test_thumbnail_is_small_webp_with_aspect_ratio() -> None:
    thumb = Image.open(io.BytesIO(make_thumbnail(_jpeg((4000, 3000)), 480)))

    assert thumb.format == "WEBP"
    assert thumb.size == (480, 360)


def test_thumbnail_applies_exif_rotation() -> None:
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90° to display
    thumb = make_thumbnail(_jpeg((800, 400), exif=exif.tobytes()), 480)

    assert Image.open(io.BytesIO(thumb)).size == (240, 480)


def test_thumbnail_rejects_non_images() -> None:
    with pytest.raises(InvalidImageError):
        make_thumbnail(b"not an image", 480)


# --- URLs -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("endpoint", "secure", "expected"),
    [
        ("https://files.example.com", False, "https://files.example.com"),
        ("https://files.example.com/", None, "https://files.example.com"),
        ("localhost:9000", False, "http://localhost:9000"),
        ("files.example.com", True, "https://files.example.com"),
    ],
)
def test_public_base_url(endpoint: str, secure: bool | None, expected: str) -> None:
    assert MinioClientWrapper._base_url(endpoint, secure) == expected


def test_public_url_is_stable_and_quoted(real_minio_client: MinioClientWrapper) -> None:
    first = real_minio_client.public_url("caps", "thumbs/a b.jpg.webp")

    assert first == real_minio_client.public_url("caps", "thumbs/a b.jpg.webp")
    assert first.endswith("/caps/thumbs/a%20b.jpg.webp")
    assert "X-Amz" not in first


def test_response_includes_thumbnail_url_only_when_present() -> None:
    facade = MagicMock()
    facade.get_image_url.side_effect = lambda key: f"http://img/{key}"
    cap = MagicMock(
        s3_key="caps/x.jpg",
        thumbnail_s3_key="thumbs/caps/x.jpg.webp",
        variant_name=None,
        collected_date=None,
    )
    cap.beer.country = None
    cap.beer.beer_brand = None
    cap.beer.name = "Beer"
    cap.beer.rating = 0
    cap.beer_id = 1
    cap.id = 1

    with_thumb = build_beer_cap_response(cap, facade)
    cap.thumbnail_s3_key = None
    without = build_beer_cap_response(cap, facade)

    assert with_thumb.presigned_url == "http://img/caps/x.jpg"
    assert with_thumb.thumbnail_url == "http://img/thumbs/caps/x.jpg.webp"
    assert without.thumbnail_url is None


# --- create / delete / backfill --------------------------------------------


async def test_create_stores_cacheable_original_and_thumbnail(
    db_session: AsyncSession, real_minio_client: MinioClientWrapper
) -> None:
    facade = _facade(db_session, real_minio_client)
    data = _jpeg((1200, 1200))

    cap = await facade.create_cap_for_existing_beer_and_upload(
        await _beer_id(db_session),
        BeerCapCreateSchema(filename="image.jpg"),
        io.BytesIO(data),
        len(data),
        content_type="image/jpeg",
    )

    assert cap and cap.thumbnail_s3_key == thumbnail_object_name(cap.s3_key)
    stored = real_minio_client.download_bytes(TEST_BUCKET_NAME, cap.thumbnail_s3_key)
    assert Image.open(io.BytesIO(stored)).size == (480, 480)
    for key in (cap.s3_key, cap.thumbnail_s3_key):
        stat = real_minio_client.client.stat_object(TEST_BUCKET_NAME, key)
        assert stat.metadata["Cache-Control"] == IMMUTABLE_CACHE_CONTROL


async def test_unreadable_image_still_creates_cap_without_thumbnail(
    db_session: AsyncSession, mock_minio_client_wrapper: MagicMock
) -> None:
    facade = _facade(db_session, mock_minio_client_wrapper)

    cap = await facade.create_cap_for_existing_beer_and_upload(
        await _beer_id(db_session),
        BeerCapCreateSchema(filename="cap.jpg"),
        io.BytesIO(b"x"),
        1,
        content_type="image/jpeg",
    )

    assert cap and cap.thumbnail_s3_key is None
    assert mock_minio_client_wrapper.upload_file.call_count == 1


async def test_failed_commit_removes_original_and_thumbnail(
    db_session: AsyncSession, mock_minio_client_wrapper: MagicMock
) -> None:
    facade = _facade(db_session, mock_minio_client_wrapper)
    beer_id = await _beer_id(db_session)
    db_session.commit = AsyncMock(side_effect=RuntimeError("commit failed"))  # type: ignore[method-assign]
    data = _jpeg((100, 100))

    with pytest.raises(RuntimeError):
        await facade.create_cap_for_existing_beer_and_upload(
            beer_id,
            BeerCapCreateSchema(filename="cap.jpg"),
            io.BytesIO(data),
            len(data),
            content_type="image/jpeg",
        )

    uploaded = [c.args[1] for c in mock_minio_client_wrapper.upload_file.call_args_list]
    deleted = [c.args[1] for c in mock_minio_client_wrapper.delete_file.call_args_list]
    assert len(uploaded) == 2 and sorted(deleted) == sorted(uploaded)


async def test_delete_removes_thumbnail(
    db_session: AsyncSession, mock_minio_client_wrapper: MagicMock
) -> None:
    facade = _facade(db_session, mock_minio_client_wrapper)
    data = _jpeg((100, 100))
    cap = await facade.create_cap_for_existing_beer_and_upload(
        await _beer_id(db_session),
        BeerCapCreateSchema(filename="cap.jpg"),
        io.BytesIO(data),
        len(data),
        content_type="image/jpeg",
    )
    assert cap and cap.thumbnail_s3_key

    await facade.delete_beer_cap_and_its_augmented_caps(cap.id)

    mock_minio_client_wrapper.delete_file.assert_any_call(
        TEST_BUCKET_NAME, cap.thumbnail_s3_key
    )


async def test_backfill_creates_missing_thumbnails_and_is_idempotent(
    db_session: AsyncSession, real_minio_client: MinioClientWrapper
) -> None:
    facade = _facade(db_session, real_minio_client)
    beer_id = await _beer_id(db_session)
    data = _jpeg((900, 600))
    real_minio_client.upload_file(
        TEST_BUCKET_NAME, "legacy.jpg", io.BytesIO(data), len(data), "image/jpeg"
    )
    legacy = await create_beer_cap(
        db_session, beer_id, "legacy.jpg", BeerCapCreateSchema(filename="x")
    )
    # Its image is missing from storage: skipped now, retried on the next run.
    missing = await create_beer_cap(
        db_session, beer_id, "missing.jpg", BeerCapCreateSchema(filename="y")
    )
    legacy_id, missing_id = legacy.id, missing.id

    assert await facade.backfill_thumbnails() == 1
    assert await facade.backfill_thumbnails() == 0

    db_session.expunge_all()
    legacy_cap = await get_beer_cap_by_id(db_session, legacy_id)
    missing_cap = await get_beer_cap_by_id(db_session, missing_id)
    assert legacy_cap and legacy_cap.thumbnail_s3_key == "thumbs/legacy.jpg.webp"
    assert missing_cap and missing_cap.thumbnail_s3_key is None
    thumb = real_minio_client.download_bytes(
        TEST_BUCKET_NAME, legacy_cap.thumbnail_s3_key
    )
    assert Image.open(io.BytesIO(thumb)).size == (480, 320)
