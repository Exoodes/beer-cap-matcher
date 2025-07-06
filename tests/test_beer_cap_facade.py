import io
from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.crud_augmented_cap import get_all_augmented_caps, get_augmented_cap_by_id
from src.db.crud_beer import get_beer_by_id
from src.db.crud_beer_cap import get_beer_cap_by_id
from src.facades.beer_cap_facade import BeerCapFacade
from src.schemas.augmented_cap_schema import AugmentedCapCreateSchema
from src.schemas.beer_cap_schema import BeerCapCreateSchema
from tests.conftest import TEST_BUCKET_NAME, TEST_IMAGE_CONTENT_TYPE, TEST_MINIO_ENDPOINT


@pytest.mark.asyncio
class TestBeerCapFacade:

    async def test_create_beer_with_cap_and_upload(
        self,
        db_session: AsyncSession,
        mock_minio_client_wrapper: MagicMock,
        dummy_image_bytes: bytes,
        dummy_image_file_like: io.BytesIO,
    ):
        facade = BeerCapFacade(minio_wrapper=mock_minio_client_wrapper)

        beer_name = "Facade Beer 1"
        cap_filename = "cap_facade_001.jpg"
        cap_metadata = BeerCapCreateSchema(filename=cap_filename, metadata={"source": "test"})

        dummy_image_file_like.seek(0)

        beer_cap = await facade.create_beer_with_cap_and_upload(
            beer_name=beer_name,
            cap_metadata=cap_metadata,
            image_data=dummy_image_file_like,
            image_length=len(dummy_image_bytes),
            content_type=TEST_IMAGE_CONTENT_TYPE,
            db_session=db_session,
        )

        assert beer_cap is not None
        assert beer_cap.id is not None
        assert beer_cap.s3_key == cap_filename

        mock_minio_client_wrapper.upload_file.assert_called_once_with(
            bucket_name=TEST_BUCKET_NAME,
            object_name=cap_filename,
            data=dummy_image_file_like,
            length=len(dummy_image_bytes),
            content_type=TEST_IMAGE_CONTENT_TYPE,
        )

        fetched_beer = await get_beer_by_id(db_session, beer_cap.beer_id)
        assert fetched_beer is not None
        assert fetched_beer.name == beer_name

        fetched_cap = await get_beer_cap_by_id(db_session, beer_cap.id)
        assert fetched_cap is not None
        assert fetched_cap.s3_key == mock_minio_client_wrapper.upload_file.return_value
        assert fetched_cap.metadata == {"source": "test"}

        print(f"✅ test_create_beer_with_cap_and_upload passed for {cap_filename}")

    async def test_add_augmented_cap_and_upload(
        self,
        db_session: AsyncSession,
        mock_minio_client_wrapper: MagicMock,
        dummy_image_bytes: bytes,
        dummy_image_file_like: io.BytesIO,
    ):
        facade = BeerCapFacade(minio_wrapper=mock_minio_client_wrapper)

        base_beer = await facade.create_beer_with_cap_and_upload(
            beer_name="Base Beer for Augment",
            cap_metadata=BeerCapCreateSchema(filename="base_cap.jpg", metadata={}),
            image_data=io.BytesIO(b"base image"),
            image_length=len(b"base image"),
            content_type=TEST_IMAGE_CONTENT_TYPE,
            db_session=db_session,
        )
        base_cap_id = base_beer.id

        mock_minio_client_wrapper.upload_file.reset_mock()
        mock_minio_client_wrapper.generate_presigned_url.reset_mock()

        aug_filename = "augmented_cap_001.jpg"
        aug_metadata = AugmentedCapCreateSchema(filename=aug_filename, metadata={"process": "rotation"})

        dummy_image_file_like.seek(0)

        aug_cap = await facade.add_augmented_cap_and_upload(
            beer_cap_id=base_cap_id,
            aug_metadata=aug_metadata,
            image_data=dummy_image_file_like,
            image_length=len(dummy_image_bytes),
            content_type=TEST_IMAGE_CONTENT_TYPE,
            db_session=db_session,
        )

        assert aug_cap is not None
        assert aug_cap.id is not None
        assert aug_cap.beer_cap_id == base_cap_id
        assert aug_cap.s3_key == aug_filename

        mock_minio_client_wrapper.upload_file.assert_called_once_with(
            bucket_name=TEST_BUCKET_NAME,
            object_name=aug_filename,
            data=dummy_image_file_like,
            length=len(dummy_image_bytes),
            content_type=TEST_IMAGE_CONTENT_TYPE,
        )

        fetched_aug_cap = await get_augmented_cap_by_id(db_session, aug_cap.id)
        assert fetched_aug_cap is not None
        assert fetched_aug_cap.s3_key == mock_minio_client_wrapper.upload_file.return_value
        assert fetched_aug_cap.metadata == {"process": "rotation"}
        print(f"✅ test_add_augmented_cap_and_upload passed for {aug_filename}")

    async def test_get_presigned_url_for_cap(self, mock_minio_client_wrapper: MagicMock):
        facade = BeerCapFacade(minio_wrapper=mock_minio_client_wrapper)

        original_s3_key = "original_cap_key_for_url.jpg"
        presigned_url_original = facade.get_presigned_url_for_cap(original_s3_key, is_augmented=False)

        mock_minio_client_wrapper.generate_presigned_url.assert_called_once_with(TEST_BUCKET_NAME, original_s3_key)
        assert presigned_url_original == f"{TEST_MINIO_ENDPOINT}/{TEST_BUCKET_NAME}/{original_s3_key}"

        mock_minio_client_wrapper.generate_presigned_url.reset_mock()

        augmented_s3_key = "augmented_cap_key_for_url.jpg"
        presigned_url_augmented = facade.get_presigned_url_for_cap(augmented_s3_key, is_augmented=True)

        mock_minio_client_wrapper.generate_presigned_url.assert_called_once_with(TEST_BUCKET_NAME, augmented_s3_key)
        assert presigned_url_augmented == f"{TEST_MINIO_ENDPOINT}/{TEST_BUCKET_NAME}/{augmented_s3_key}"

        print("✅ test_get_presigned_url_for_cap passed")

    async def test_delete_augmented_caps(
        self,
        db_session: AsyncSession,
        mock_minio_client_wrapper: MagicMock,
        dummy_image_bytes: bytes,
        dummy_image_file_like: io.BytesIO,
    ):
        facade = BeerCapFacade(minio_wrapper=mock_minio_client_wrapper)

        base_beer = await facade.create_beer_with_cap_and_upload(
            beer_name="Base Beer for Delete Aug",
            cap_metadata=BeerCapCreateSchema(filename="delete_base.jpg", metadata={}),
            image_data=io.BytesIO(b"base data"),
            image_length=len(b"base data"),
            content_type=TEST_IMAGE_CONTENT_TYPE,
            db_session=db_session,
        )
        base_cap_id = base_beer.id

        aug_files = [f"aug_{i}.jpg" for i in range(3)]
        aug_caps = []
        for filename in aug_files:
            dummy_image_file_like.seek(0)
            aug = await facade.add_augmented_cap_and_upload(
                beer_cap_id=base_cap_id,
                aug_metadata=AugmentedCapCreateSchema(filename=filename),
                image_data=dummy_image_file_like,
                image_length=len(dummy_image_bytes),
                content_type=TEST_IMAGE_CONTENT_TYPE,
                db_session=db_session,
            )
            aug_caps.append(aug)

        mock_minio_client_wrapper.delete_file.reset_mock()

        await facade.delete_augmented_caps(base_cap_id, db_session=db_session)

        for aug_cap in aug_caps:
            mock_minio_client_wrapper.delete_file.assert_any_call(TEST_BUCKET_NAME, aug_cap.s3_key)
        assert mock_minio_client_wrapper.delete_file.call_count == len(aug_files)

        remaining_augs = await get_all_augmented_caps(db_session)
        assert all(aug.id != ac.id for ac in aug_caps for aug in remaining_augs)
        print("✅ test_delete_augmented_caps passed")

    async def test_delete_beer_cap_and_its_augmented_caps(
        self,
        db_session: AsyncSession,
        mock_minio_client_wrapper: MagicMock,
        dummy_image_bytes: bytes,
        dummy_image_file_like: io.BytesIO,
    ):
        facade = BeerCapFacade(minio_wrapper=mock_minio_client_wrapper)

        beer_name = "Beer to Delete"
        cap_filename = "main_cap_to_delete.jpg"
        main_beer = await facade.create_beer_with_cap_and_upload(
            beer_name=beer_name,
            cap_metadata=BeerCapCreateSchema(filename=cap_filename),
            image_data=io.BytesIO(dummy_image_bytes),
            image_length=len(dummy_image_bytes),
            content_type=TEST_IMAGE_CONTENT_TYPE,
            db_session=db_session,
        )
        main_cap_id = main_beer.id
        main_cap_s3_key = main_beer.s3_key

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
                db_session=db_session,
            )
            aug_s3_keys.append(aug_cap.s3_key)

        mock_minio_client_wrapper.delete_file.reset_mock()

        await facade.delete_beer_cap_and_its_augmented_caps(main_cap_id, db_session=db_session)

        expected_deleted_s3_keys = [main_cap_s3_key] + aug_s3_keys
        for s3_key in expected_deleted_s3_keys:
            mock_minio_client_wrapper.delete_file.assert_any_call(TEST_BUCKET_NAME, s3_key)
        assert mock_minio_client_wrapper.delete_file.call_count == len(expected_deleted_s3_keys)

        deleted_main_cap = await get_beer_cap_by_id(db_session, main_cap_id)
        assert deleted_main_cap is None

        for s3_key in aug_s3_keys:
            pass

        fetched_beer = await get_beer_by_id(db_session, main_beer.beer_id)
        assert fetched_beer is not None
        print("✅ test_delete_beer_cap_and_its_augmented_caps passed")
