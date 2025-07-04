import asyncio
import io
from pathlib import Path

from sqlalchemy import text

from src.database import async_session
from src.db.crud_augmented_cap import (
    create_augmented_cap,
    delete_augmented_cap,
    get_all_augmented_caps,
    get_augmented_cap_by_id,
)
from src.db.crud_beer import create_beer, delete_beer, get_all_beers, get_beer_by_id
from src.db.crud_beer_cap import create_beer_cap, delete_beer_cap, get_all_beer_caps, get_beer_cap_by_id
from src.facades.beer_cap_facade import BeerCapFacade
from src.models.augmented_cap import AugmentedCap
from src.models.beer import Beer
from src.models.beer_cap import BeerCap
from src.s3.minio_client import MinioClientWrapper
from src.schemas.augmented_cap_schema import AugmentedCapCreateSchema
from src.schemas.beer_cap_schema import BeerCapCreateSchema


async def test_postgres_crud():
    async with async_session() as session:
        await session.execute(text("TRUNCATE TABLE augmented_caps, beer_caps, beers RESTART IDENTITY CASCADE;"))
        await session.commit()
        print("All tables truncated.")

    async with async_session() as session:
        beer = await create_beer(session, "Test Beer")
        assert isinstance(beer, Beer)
        assert beer.id is not None
        assert beer.name == "Test Beer"
        print(f"Created beer: {beer.id} - {beer.name}")

    async with async_session() as session:
        created_beer = await create_beer(session, "ID Test Beer")
        fetched_beer = await get_beer_by_id(session, created_beer.id)
        assert fetched_beer is not None
        assert fetched_beer.id == created_beer.id
        assert fetched_beer.name == "ID Test Beer"
        print(f"Fetched beer: {fetched_beer.id} - {fetched_beer.name}")

    async with async_session() as session:
        await create_beer(session, "Beer One")
        await create_beer(session, "Beer Two")
        beers = await get_all_beers(session)
        assert len(beers) >= 2
        names = [beer.name for beer in beers]
        assert "Beer One" in names
        assert "Beer Two" in names
        print(f"All beers: {[beer.name for beer in beers]}")

    async with async_session() as session:
        created_beer = await create_beer(session, "Delete Test Beer")
        beer_id = created_beer.id

        await delete_beer(session, beer_id)
        deleted_beer = await get_beer_by_id(session, beer_id)
        assert deleted_beer is None
        print(f"Deleted beer with ID: {beer_id}")

    async with async_session() as session:
        # Adjust beer_id to a valid existing Beer.id in your DB for real tests
        beer_id = 1

        cap = await create_beer_cap(session, beer_id, "test_cap_s3_key.jpg")
        assert isinstance(cap, BeerCap)
        assert cap.id is not None
        assert cap.beer_id == beer_id
        assert cap.s3_key == "test_cap_s3_key.jpg"
        print(f"Created beer cap: {cap.id} - {cap.s3_key}")

    async with async_session() as session:
        fetched_cap = await get_beer_cap_by_id(session, cap.id)
        assert fetched_cap is not None
        assert fetched_cap.id == cap.id
        assert fetched_cap.s3_key == "test_cap_s3_key.jpg"
        print(f"Fetched beer cap: {fetched_cap.id} - {fetched_cap.s3_key}")

    async with async_session() as session:
        all_caps = await get_all_beer_caps(session)
        assert len(all_caps) >= 1
        print(f"All beer caps: {[c.s3_key for c in all_caps]}")

    async with async_session() as session:
        new_cap = await create_beer_cap(session, beer_id, "delete_test_cap.jpg")
        assert new_cap is not None
        await delete_beer_cap(session, new_cap.id)
        deleted_cap = await get_beer_cap_by_id(session, new_cap.id)
        assert deleted_cap is None
        print(f"Deleted beer cap with ID: {new_cap.id}")

    async with async_session() as session:
        beer_cap_id = 1

        aug = await create_augmented_cap(session, beer_cap_id, "test_s3_key.jpg")
        assert isinstance(aug, AugmentedCap)
        assert aug.id is not None
        assert aug.beer_cap_id == beer_cap_id
        assert aug.s3_key == "test_s3_key.jpg"
        print(f"Created augmented cap: {aug.id} - {aug.s3_key}")

    async with async_session() as session:
        fetched_aug = await get_augmented_cap_by_id(session, aug.id)
        assert fetched_aug is not None
        assert fetched_aug.id == aug.id
        assert fetched_aug.s3_key == "test_s3_key.jpg"
        print(f"Fetched augmented cap: {fetched_aug.id} - {fetched_aug.s3_key}")

    async with async_session() as session:
        all_augs = await get_all_augmented_caps(session)
        assert len(all_augs) >= 1
        print(f"All augmented caps: {[a.s3_key for a in all_augs]}")

    async with async_session() as session:
        await delete_augmented_cap(session, aug.id)
        deleted_aug = await get_augmented_cap_by_id(session, aug.id)
        assert deleted_aug is None
        print(f"Deleted augmented cap with ID: {aug.id}")


BUCKET_NAME = "beer-caps"
TEST_OBJECT_NAME = "test-039.jpg"
IMAGE_PATH = Path("data/039.jpg")
CONTENT_TYPE = "image/jpeg"


def test_s3_operations():
    assert IMAGE_PATH.exists(), f"Image not found at {IMAGE_PATH}"

    minio_wrapper = MinioClientWrapper()

    with open(IMAGE_PATH, "rb") as f:
        image_bytes = f.read()

    file_like = io.BytesIO(image_bytes)

    uploaded_object_name = minio_wrapper.upload_file(
        bucket_name=BUCKET_NAME,
        object_name=TEST_OBJECT_NAME,
        data=file_like,
        length=len(image_bytes),
        content_type=CONTENT_TYPE,
    )

    assert uploaded_object_name == TEST_OBJECT_NAME
    print(f"✅ Uploaded file: {uploaded_object_name}")

    downloaded_data = minio_wrapper.download_bytes(BUCKET_NAME, TEST_OBJECT_NAME)
    assert downloaded_data == image_bytes
    print(f"✅ Downloaded file content matches original image (size: {len(downloaded_data)} bytes)")

    presigned_url = minio_wrapper.generate_presigned_url(BUCKET_NAME, TEST_OBJECT_NAME)
    assert presigned_url.startswith("http")
    print(f"✅ Generated presigned URL: {presigned_url}")

    minio_wrapper.delete_file(BUCKET_NAME, TEST_OBJECT_NAME)
    print(f"✅ Deleted file: {TEST_OBJECT_NAME}")


async def test_beer_cap_facade():
    assert IMAGE_PATH.exists(), f"Image not found at {IMAGE_PATH}"

    minio_wrapper = MinioClientWrapper()
    facade = BeerCapFacade(minio_wrapper)

    with open(IMAGE_PATH, "rb") as f:
        image_bytes = f.read()

    file_like = io.BytesIO(image_bytes)

    cap_metadata = BeerCapCreateSchema(filename="test_cap_039.jpg", metadata={})
    beer_cap = await facade.create_beer_with_cap_and_upload(
        beer_name="Test Beer Facade",
        cap_metadata=cap_metadata,
        image_data=file_like,
        image_length=len(image_bytes),
        content_type=CONTENT_TYPE,
    )
    assert beer_cap is not None
    print(f"✅ Created BeerCap with ID {beer_cap.id} and filename {beer_cap.s3_key}")

    # Generate presigned URL for the original cap
    presigned_url = facade.get_presigned_url_for_cap(beer_cap.s3_key, is_augmented=False)
    print(f"✅ Presigned URL for original cap: {presigned_url}")

    # Add an augmented cap and upload
    aug_metadata = AugmentedCapCreateSchema(filename="augmented_test_cap_039.jpg")
    aug_file_like = io.BytesIO(image_bytes)  # Re-create BytesIO for new upload

    aug_cap = await facade.add_augmented_cap_and_upload(
        beer_cap_id=beer_cap.id,
        aug_metadata=aug_metadata,
        image_data=aug_file_like,
        image_length=len(image_bytes),
        content_type=CONTENT_TYPE,
    )
    assert aug_cap is not None
    print(f"✅ Added AugmentedCap with ID {aug_cap.id} and filename {aug_cap.s3_key}")

    # Generate presigned URL for augmented cap
    presigned_aug_url = facade.get_presigned_url_for_cap(aug_cap.s3_key, is_augmented=True)
    print(f"✅ Presigned URL for augmented cap: {presigned_aug_url}")

    # Delete augmented caps
    await facade.delete_augmented_caps(beer_cap.id)
    print(f"✅ Deleted all augmented caps for BeerCap ID {beer_cap.id}")

    # Delete beer cap and its augmented caps (should delete the cap itself)
    await facade.delete_beer_cap_and_its_augmented_caps(beer_cap.id)
    print(f"✅ Deleted BeerCap ID {beer_cap.id} and its augmented caps from DB and S3")


if __name__ == "__main__":
    asyncio.run(test_postgres_crud())
    test_s3_operations()
    asyncio.run(test_beer_cap_facade())
