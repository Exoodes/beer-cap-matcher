import io

import pytest
from minio.error import S3Error

from src.storage.minio.minio_client import MinioClientWrapper
from tests.conftest import (
    TEST_BUCKET_NAME,
    TEST_IMAGE_CONTENT_TYPE,
    TEST_MINIO_ENDPOINT,
)


class TestMinioClientIntegration:

    def test_upload_file(
        self, real_minio_client: MinioClientWrapper, dummy_image_bytes: bytes
    ):
        object_name = "test_upload.jpg"
        data_stream = io.BytesIO(dummy_image_bytes)

        uploaded_object_name = real_minio_client.upload_file(
            bucket_name=TEST_BUCKET_NAME,
            object_name=object_name,
            data=data_stream,
            length=len(dummy_image_bytes),
            content_type=TEST_IMAGE_CONTENT_TYPE,
        )

        assert uploaded_object_name == object_name

        stat = real_minio_client.client.stat_object(TEST_BUCKET_NAME, object_name)
        assert stat.size == len(dummy_image_bytes)

    def test_download_bytes(
        self, real_minio_client: MinioClientWrapper, dummy_image_bytes: bytes
    ):
        object_name = "test_download.jpg"

        upload_stream = io.BytesIO(dummy_image_bytes)
        real_minio_client.upload_file(
            bucket_name=TEST_BUCKET_NAME,
            object_name=object_name,
            data=upload_stream,
            length=len(dummy_image_bytes),
            content_type=TEST_IMAGE_CONTENT_TYPE,
        )

        downloaded_data = real_minio_client.download_bytes(
            TEST_BUCKET_NAME, object_name
        )

        assert downloaded_data == dummy_image_bytes

    def test_delete_file(
        self, real_minio_client: MinioClientWrapper, dummy_image_bytes: bytes
    ):
        object_name = "test_delete.jpg"

        upload_stream = io.BytesIO(dummy_image_bytes)
        real_minio_client.upload_file(
            bucket_name=TEST_BUCKET_NAME,
            object_name=object_name,
            data=upload_stream,
            length=len(dummy_image_bytes),
            content_type=TEST_IMAGE_CONTENT_TYPE,
        )

        real_minio_client.client.stat_object(TEST_BUCKET_NAME, object_name)

        real_minio_client.delete_file(TEST_BUCKET_NAME, object_name)

        with pytest.raises(S3Error) as excinfo:
            real_minio_client.client.stat_object(TEST_BUCKET_NAME, object_name)
        assert "NoSuchKey" in str(excinfo.value) or "Object not found" in str(
            excinfo.value
        )

    def test_generate_presigned_url(self, real_minio_client: MinioClientWrapper):
        object_name = "test_presigned_url.jpg"

        presigned_url = real_minio_client.generate_presigned_url(
            TEST_BUCKET_NAME, object_name, expiry_seconds=60
        )

        assert isinstance(presigned_url, str)
        assert presigned_url.startswith(
            f"http://{TEST_MINIO_ENDPOINT}/{TEST_BUCKET_NAME}/{object_name}"
        )

    def test_object_exists_existing(
        self, real_minio_client: MinioClientWrapper, dummy_image_bytes: bytes
    ):
        object_name = "test_exists.jpg"
        upload_stream = io.BytesIO(dummy_image_bytes)
        real_minio_client.upload_file(
            bucket_name=TEST_BUCKET_NAME,
            object_name=object_name,
            data=upload_stream,
            length=len(dummy_image_bytes),
            content_type=TEST_IMAGE_CONTENT_TYPE,
        )
        assert real_minio_client.object_exists(TEST_BUCKET_NAME, object_name) is True

    def test_object_exists_non_existing(self, real_minio_client: MinioClientWrapper):
        object_name = "non_existent_file.jpg"
        assert real_minio_client.object_exists(TEST_BUCKET_NAME, object_name) is False

    def test_ensure_buckets_exist_creates_new_bucket(
        self, real_minio_client: MinioClientWrapper
    ):
        bucket_name = "new-test-bucket"
        if real_minio_client.client.bucket_exists(bucket_name):
            real_minio_client.client.remove_bucket(bucket_name)

        real_minio_client.ensure_buckets_exist([bucket_name])
        assert real_minio_client.client.bucket_exists(bucket_name) is True
        real_minio_client.client.remove_bucket(bucket_name)

    def test_download_all_objects_parallel(
        self, real_minio_client: MinioClientWrapper, dummy_image_bytes: bytes
    ):
        object_names = [
            "test_parallel_1.jpg",
            "test_parallel_2.jpg",
            "test_parallel_3.jpg",
        ]
        for name in object_names:
            real_minio_client.upload_file(
                bucket_name=TEST_BUCKET_NAME,
                object_name=name,
                data=io.BytesIO(dummy_image_bytes),
                length=len(dummy_image_bytes),
                content_type=TEST_IMAGE_CONTENT_TYPE,
            )

        downloaded_objects = real_minio_client.download_all_objects_parallel(
            TEST_BUCKET_NAME
        )
        downloaded_names = [name for name, _ in downloaded_objects]

        assert len(downloaded_objects) == len(object_names)
        for name in object_names:
            assert name in downloaded_names
