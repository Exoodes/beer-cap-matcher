import io
from contextlib import asynccontextmanager
from datetime import date
from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.augmented_beer_cap.augmented_cap_create import AugmentedCapCreateSchema
from src.api.schemas.beer_cap.beer_cap_create import BeerCapCreateSchema
from src.api.schemas.country.country_create import CountryCreateSchema
from src.db.crud.augmented_cap_crud import get_all_augmented_caps, get_augmented_cap_by_id
from src.db.crud.beer_brand_crud import create_beer_brand
from src.db.crud.beer_cap_crud import get_all_beer_caps, get_beer_cap_by_id
from src.db.crud.beer_crud import get_all_beers, get_beer_by_id
from src.db.crud.country_crud import create_country
from src.services.beer_cap_facade import BeerCapFacade
from tests.conftest import TEST_IMAGE_CONTENT_TYPE, TEST_MINIO_ENDPOINT


@pytest.mark.asyncio
class TestBeerCapFacade:

    async def test_create_beer_with_cap_and_upload(
        self,
        db_session: AsyncSession,
        mock_minio_client_wrapper: MagicMock,
        dummy_image_bytes: bytes,
        dummy_image_file_like: io.BytesIO,
    ):
        @asynccontextmanager
        async def fake_session_maker():
            yield db_session

        facade = BeerCapFacade(minio_wrapper=mock_minio_client_wrapper, session_maker=fake_session_maker)

        beer_brand = await create_beer_brand(db_session, "Facade Beer Brand")
        beer_name = "Facade Beer 1"
        cap_filename = "cap_facade_001.jpg"
        cap_metadata = BeerCapCreateSchema(filename=cap_filename, collected_date=date.today())

        dummy_image_file_like.seek(0)

        beer_cap = await facade.create_beer_with_cap_and_upload(
            beer_name=beer_name,
            beer_brand_id=beer_brand.id,
            cap_metadata=cap_metadata,
            image_data=dummy_image_file_like,
            image_length=len(dummy_image_bytes),
            content_type=TEST_IMAGE_CONTENT_TYPE,
        )

        assert beer_cap is not None
        assert beer_cap.id is not None
        assert beer_cap.s3_key == cap_filename

        mock_minio_client_wrapper.upload_file.assert_called_once_with(
            facade.original_caps_bucket,
            cap_filename,
            dummy_image_file_like,
            len(dummy_image_bytes),
            TEST_IMAGE_CONTENT_TYPE,
        )

        fetched_beer = await get_beer_by_id(db_session, beer_cap.beer_id)
        assert fetched_beer is not None
        assert fetched_beer.name == beer_name

        fetched_cap = await get_beer_cap_by_id(db_session, beer_cap.id)
        assert fetched_cap is not None
        assert fetched_cap.s3_key == cap_filename
        assert fetched_cap.collected_date == cap_metadata.collected_date

        print(f"✅ test_create_beer_with_cap_and_upload passed for {cap_filename}")

    async def test_create_cap_and_related_entities(
        self,
        db_session: AsyncSession,
        mock_minio_client_wrapper: MagicMock,
        dummy_image_bytes: bytes,
    ):
        @asynccontextmanager
        async def fake_session_maker():
            yield db_session

        facade = BeerCapFacade(minio_wrapper=mock_minio_client_wrapper, session_maker=fake_session_maker)

        await create_beer_brand(db_session, "New Test Brand")
        await create_country(db_session, CountryCreateSchema(name="New Test Country"))

        cap_filename = "new_cap_and_entities.jpg"
        cap_metadata = BeerCapCreateSchema(
            filename=cap_filename,
            beer_name="New Test Beer",
            beer_brand_name="New Test Brand",
            country_name="New Test Country",
        )
        image_data = io.BytesIO(dummy_image_bytes)
        image_length = len(dummy_image_bytes)

        new_beer_cap = await facade.create_cap_and_related_entities(
            cap_metadata=cap_metadata,
            image_data=image_data,
            image_length=image_length,
            content_type=TEST_IMAGE_CONTENT_TYPE,
        )

        assert new_beer_cap is not None
        assert new_beer_cap.beer is not None
        assert new_beer_cap.beer.name == "New Test Beer"
        # assert new_beer_cap.beer.beer_brand.name == "New Test Brand"
        # assert new_beer_cap.beer.country.name == "New Test Country"

    async def test_add_augmented_cap_and_upload(
        self,
        db_session: AsyncSession,
        mock_minio_client_wrapper: MagicMock,
        dummy_image_bytes: bytes,
        dummy_image_file_like: io.BytesIO,
    ):
        @asynccontextmanager
        async def fake_session_maker():
            yield db_session

        facade = BeerCapFacade(minio_wrapper=mock_minio_client_wrapper, session_maker=fake_session_maker)

        beer_brand = await create_beer_brand(db_session, "Augmented Beer Brand")
        base_beer_cap = await facade.create_beer_with_cap_and_upload(
            beer_name="Base Beer for Augment",
            beer_brand_id=beer_brand.id,
            cap_metadata=BeerCapCreateSchema(filename="base_cap.jpg"),
            image_data=io.BytesIO(b"base image"),
            image_length=len(b"base image"),
            content_type=TEST_IMAGE_CONTENT_TYPE,
        )
        base_cap_id = base_beer_cap.id

        mock_minio_client_wrapper.upload_file.reset_mock()

        aug_filename = "augmented_cap_001.jpg"
        aug_metadata = AugmentedCapCreateSchema(filename=aug_filename)

        dummy_image_file_like.seek(0)

        aug_cap = await facade.add_augmented_cap_and_upload(
            beer_cap_id=base_cap_id,
            aug_metadata=aug_metadata,
            image_data=dummy_image_file_like,
            image_length=len(dummy_image_bytes),
            content_type=TEST_IMAGE_CONTENT_TYPE,
        )

        assert aug_cap is not None
        assert aug_cap.id is not None
        assert aug_cap.beer_cap_id == base_cap_id
        assert aug_cap.s3_key == aug_filename

        mock_minio_client_wrapper.upload_file.assert_called_once_with(
            facade.augmented_caps_bucket,
            aug_filename,
            dummy_image_file_like,
            len(dummy_image_bytes),
            TEST_IMAGE_CONTENT_TYPE,
        )

        fetched_aug_cap = await get_augmented_cap_by_id(db_session, aug_cap.id)
        assert fetched_aug_cap is not None
        assert fetched_aug_cap.s3_key == aug_filename
        print(f"✅ test_add_augmented_cap_and_upload passed for {aug_filename}")

    async def test_get_presigned_url_for_cap(self, mock_minio_client_wrapper: MagicMock):
        facade = BeerCapFacade(minio_wrapper=mock_minio_client_wrapper)

        original_s3_key = "original_cap_key_for_url.jpg"
        expected_url_original = f"{TEST_MINIO_ENDPOINT}/{facade.original_caps_bucket}/{original_s3_key}"
        mock_minio_client_wrapper.generate_presigned_url.return_value = expected_url_original

        presigned_url_original = facade.get_presigned_url_for_cap(original_s3_key, is_augmented=False)

        mock_minio_client_wrapper.generate_presigned_url.assert_called_once_with(
            facade.original_caps_bucket, original_s3_key
        )
        assert presigned_url_original == expected_url_original

        mock_minio_client_wrapper.generate_presigned_url.reset_mock()

        augmented_s3_key = "augmented_cap_key_for_url.jpg"
        expected_url_augmented = f"{TEST_MINIO_ENDPOINT}/{facade.augmented_caps_bucket}/{augmented_s3_key}"
        mock_minio_client_wrapper.generate_presigned_url.return_value = expected_url_augmented

        presigned_url_augmented = facade.get_presigned_url_for_cap(augmented_s3_key, is_augmented=True)

        mock_minio_client_wrapper.generate_presigned_url.assert_called_once_with(
            facade.augmented_caps_bucket, augmented_s3_key
        )
        assert presigned_url_augmented == expected_url_augmented

        print("✅ test_get_presigned_url_for_cap passed")

    async def test_delete_augmented_caps(
        self,
        db_session: AsyncSession,
        mock_minio_client_wrapper: MagicMock,
        dummy_image_bytes: bytes,
        dummy_image_file_like: io.BytesIO,
    ):
        @asynccontextmanager
        async def fake_session_maker():
            yield db_session

        facade = BeerCapFacade(minio_wrapper=mock_minio_client_wrapper, session_maker=fake_session_maker)

        beer_brand = await create_beer_brand(db_session, "Augmented Beer Brand for Delete")
        base_beer_cap = await facade.create_beer_with_cap_and_upload(
            beer_name="Base Beer for Delete Aug",
            beer_brand_id=beer_brand.id,
            cap_metadata=BeerCapCreateSchema(filename="delete_base.jpg"),
            image_data=io.BytesIO(b"base data"),
            image_length=len(b"base data"),
            content_type=TEST_IMAGE_CONTENT_TYPE,
        )
        base_cap_id = base_beer_cap.id

        aug_files = [f"aug_{i}.jpg" for i in range(3)]
        aug_caps = []
        for filename in aug_files:
            fresh_file_like = io.BytesIO(dummy_image_bytes)
            aug = await facade.add_augmented_cap_and_upload(
                beer_cap_id=base_cap_id,
                aug_metadata=AugmentedCapCreateSchema(filename=filename),
                image_data=fresh_file_like,
                image_length=len(dummy_image_bytes),
                content_type=TEST_IMAGE_CONTENT_TYPE,
            )
            aug_caps.append(aug)

        mock_minio_client_wrapper.delete_file.reset_mock()

        await db_session.refresh(base_beer_cap)
        await facade.delete_augmented_caps(base_cap_id)

        for aug_cap in aug_caps:
            mock_minio_client_wrapper.delete_file.assert_any_call(facade.augmented_caps_bucket, aug_cap.s3_key)
        assert mock_minio_client_wrapper.delete_file.call_count == len(aug_files)

        remaining_augs = await get_all_augmented_caps(db_session)
        assert all(aug.id != ac.id for ac in aug_caps for aug in remaining_augs)
        print("✅ test_delete_augmented_caps passed")

    async def test_delete_all_augmented_caps(
        self,
        db_session: AsyncSession,
        mock_minio_client_wrapper: MagicMock,
        dummy_image_bytes: bytes,
    ):
        @asynccontextmanager
        async def fake_session_maker():
            yield db_session

        facade = BeerCapFacade(minio_wrapper=mock_minio_client_wrapper, session_maker=fake_session_maker)

        beer_brand = await create_beer_brand(db_session, "Delete All Augs Brand")
        base_cap = await facade.create_beer_with_cap_and_upload(
            beer_name="Base Beer for Delete All",
            beer_brand_id=beer_brand.id,
            cap_metadata=BeerCapCreateSchema(filename="base_cap_for_delete_all.jpg"),
            image_data=io.BytesIO(dummy_image_bytes),
            image_length=len(dummy_image_bytes),
            content_type=TEST_IMAGE_CONTENT_TYPE,
        )

        await facade.add_augmented_cap_and_upload(
            beer_cap_id=base_cap.id,
            aug_metadata=AugmentedCapCreateSchema(filename="aug_1.jpg"),
            image_data=io.BytesIO(dummy_image_bytes),
            image_length=len(dummy_image_bytes),
            content_type=TEST_IMAGE_CONTENT_TYPE,
        )
        await facade.add_augmented_cap_and_upload(
            beer_cap_id=base_cap.id,
            aug_metadata=AugmentedCapCreateSchema(filename="aug_2.jpg"),
            image_data=io.BytesIO(dummy_image_bytes),
            image_length=len(dummy_image_bytes),
            content_type=TEST_IMAGE_CONTENT_TYPE,
        )

        mock_minio_client_wrapper.delete_file.reset_mock()
        deleted_count = await facade.delete_all_augmented_caps()

        assert deleted_count == 2
        mock_minio_client_wrapper.delete_file.assert_any_call(facade.augmented_caps_bucket, "aug_1.jpg")
        mock_minio_client_wrapper.delete_file.assert_any_call(facade.augmented_caps_bucket, "aug_2.jpg")
        all_augs = await get_all_augmented_caps(db_session)
        assert len(all_augs) == 0

    async def test_delete_beer_and_caps(
        self,
        db_session: AsyncSession,
        mock_minio_client_wrapper: MagicMock,
        dummy_image_bytes: bytes,
        dummy_image_file_like: io.BytesIO,
    ):
        @asynccontextmanager
        async def fake_session_maker():
            yield db_session

        facade = BeerCapFacade(minio_wrapper=mock_minio_client_wrapper, session_maker=fake_session_maker)

        beer_brand = await create_beer_brand(db_session, "Beer Brand for Deletion")
        beer_name = "Beer to Delete"
        cap_filename = "main_cap_to_delete.jpg"
        main_beer_cap = await facade.create_beer_with_cap_and_upload(
            beer_name=beer_name,
            beer_brand_id=beer_brand.id,
            cap_metadata=BeerCapCreateSchema(filename=cap_filename),
            image_data=io.BytesIO(dummy_image_bytes),
            image_length=len(dummy_image_bytes),
            content_type=TEST_IMAGE_CONTENT_TYPE,
        )
        main_cap_id = main_beer_cap.id
        main_cap_s3_key = main_beer_cap.s3_key

        aug_files = [f"aug_delete_{i}.jpg" for i in range(2)]
        aug_s3_keys = []
        for filename in aug_files:
            dummy_image_file_like.seek(0)
            aug_cap = await facade.add_augmented_cap_and_upload(
                beer_cap_id=main_cap_id,
                aug_metadata=AugmentedCapCreateSchema(filename=filename),
                image_data=dummy_image_file_like,
                image_length=len(dummy_image_bytes),
                content_type=TEST_IMAGE_CONTENT_TYPE,
            )
            aug_s3_keys.append(aug_cap.s3_key)

        mock_minio_client_wrapper.delete_file.reset_mock()

        deleted = await facade.delete_beer_and_caps(main_beer_cap.beer.id)
        assert deleted is True

        expected_deleted_s3_keys = [main_cap_s3_key] + aug_s3_keys
        for s3_key in expected_deleted_s3_keys:
            bucket = facade.augmented_caps_bucket if s3_key in aug_s3_keys else facade.original_caps_bucket
            mock_minio_client_wrapper.delete_file.assert_any_call(bucket, s3_key)
        assert mock_minio_client_wrapper.delete_file.call_count == len(expected_deleted_s3_keys)

        deleted_main_cap = await get_beer_cap_by_id(db_session, main_cap_id)
        assert deleted_main_cap is None

        fetched_beer = await get_beer_by_id(db_session, main_beer_cap.beer_id)
        assert fetched_beer is None
        print("✅ test_delete_beer_and_caps passed")
