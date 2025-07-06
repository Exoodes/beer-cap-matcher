import asyncio
import io
import os
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock

import pytest
from dotenv import load_dotenv
from pytest_asyncio import fixture as async_fixture
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db_resources
from src.db.entities import Base
from src.storage.minio_client import MinioClientWrapper

load_dotenv()

TEST_BUCKET_NAME = os.getenv("TEST_MINIO_BUCKET_NAME")
TEST_DUMMY_IMAGE_PATH = Path("tests/data/test_image.jpg")
TEST_IMAGE_CONTENT_TYPE = "image/jpeg"

TEST_POSTGRES_DATABASE_URL = os.getenv("TEST_POSTGRES_DATABASE_URL")
if not TEST_POSTGRES_DATABASE_URL:
    raise ValueError("TEST_POSTGRES_DATABASE_URL environment variable is not set in .env or your shell.")

TEST_MINIO_ENDPOINT = os.getenv("TEST_MINIO_URL")
TEST_MINIO_ACCESS_KEY = os.getenv("TEST_MINIO_ACCESS_KEY")
TEST_MINIO_SECRET_KEY = os.getenv("TEST_MINIO_SECRET_KEY")

if not all([TEST_MINIO_ENDPOINT, TEST_MINIO_ACCESS_KEY, TEST_MINIO_SECRET_KEY]):
    raise ValueError("One or more TEST_MINIO_* environment variables are not set in .env or your shell.")


@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@async_fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine, AsyncSessionLocal = get_db_resources(TEST_POSTGRES_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        yield session

    await engine.dispose()


@pytest.fixture(scope="function")
def mock_minio_client_wrapper() -> MagicMock:
    mock_minio = MagicMock(spec=MinioClientWrapper)
    mock_s3_key = "mock_s3_key.jpg"
    mock_minio.upload_file.return_value = mock_s3_key
    mock_minio.download_bytes.return_value = b"mock image data"
    mock_minio.generate_presigned_url.return_value = f"{TEST_MINIO_ENDPOINT}/{TEST_BUCKET_NAME}/{mock_s3_key}"
    mock_minio.delete_file.return_value = None
    return mock_minio


@pytest.fixture(scope="function")
def real_minio_client() -> Generator[MinioClientWrapper, None, None]:
    client = MinioClientWrapper(
        endpoint=TEST_MINIO_ENDPOINT,
        access_key=TEST_MINIO_ACCESS_KEY,
        secret_key=TEST_MINIO_SECRET_KEY,
        secure=os.getenv("MINIO_SECURE", "false").lower() == "true",
    )
    client.ensure_buckets_exist([TEST_BUCKET_NAME])
    yield client
    try:
        for obj in client.client.list_objects(TEST_BUCKET_NAME, recursive=True):
            client.client.remove_object(TEST_BUCKET_NAME, obj.object_name)
        client.client.remove_bucket(TEST_BUCKET_NAME)
    except Exception as e:
        print(f"Warning: Failed to clean up Minio bucket '{TEST_BUCKET_NAME}': {e}")


@pytest.fixture(scope="function")
def dummy_image_bytes() -> bytes:
    with open(TEST_DUMMY_IMAGE_PATH, "rb") as f:
        return f.read()


@pytest.fixture(scope="function")
def dummy_image_file_like(dummy_image_bytes: bytes) -> io.BytesIO:
    return io.BytesIO(dummy_image_bytes)
