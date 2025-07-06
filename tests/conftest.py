import asyncio
import io
import os
from collections.abc import AsyncGenerator
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from dotenv import load_dotenv
from pytest_asyncio import fixture as async_fixture
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db_resources
from src.models import Base
from src.s3.minio_client import MinioClientWrapper

TEST_BUCKET_NAME = "test-beer-caps"
TEST_DUMMY_IMAGE_PATH = Path("tests/data/test_image.jpg")
TEST_IMAGE_CONTENT_TYPE = "image/jpeg"


load_dotenv()

TEST_DATABASE_URL = os.getenv("TEST_POSTGRES_DATABASE_URL")
if not TEST_DATABASE_URL:
    raise ValueError("TEST_POSTGRES_DATABASE_URL environment variable is not set. Please configure your test database.")


@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@async_fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine, AsyncSessionLocal = get_db_resources(TEST_DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        yield session

    await engine.dispose()


@pytest.fixture(scope="function")
def mock_minio_client_wrapper() -> MagicMock:
    mock_minio = MagicMock(spec=MinioClientWrapper)
    mock_minio.upload_file.return_value = "mock_s3_key.jpg"
    mock_minio.download_bytes.return_value = b"mock image data"
    mock_minio.generate_presigned_url.return_value = f"http://mock-presigned-url/{TEST_BUCKET_NAME}/mock_s3_key.jpg"
    mock_minio.delete_file.return_value = None
    return mock_minio


@pytest.fixture(scope="function")
def dummy_image_bytes() -> bytes:
    with open(TEST_DUMMY_IMAGE_PATH, "rb") as f:
        return f.read()


@pytest.fixture(scope="function")
def dummy_image_file_like(dummy_image_bytes: bytes) -> io.BytesIO:
    return io.BytesIO(dummy_image_bytes)
