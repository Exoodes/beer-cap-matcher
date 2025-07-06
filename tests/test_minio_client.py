import io

import pytest
from minio.error import S3Error

from src.storage.minio_client import MinioClientWrapper
from tests.conftest import TEST_BUCKET_NAME, TEST_IMAGE_CONTENT_TYPE, TEST_MINIO_ENDPOINT


class TestMinioClientIntegration:

    def test_upload_file(self, real_minio_client: MinioClientWrapper, dummy_image_bytes: bytes):
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
        print(f"✅ Uploaded and verified: {object_name} (size: {stat.size})")

    def test_download_bytes(self, real_minio_client: MinioClientWrapper, dummy_image_bytes: bytes):
        object_name = "test_download.jpg"

        upload_stream = io.BytesIO(dummy_image_bytes)
        real_minio_client.upload_file(
            bucket_name=TEST_BUCKET_NAME,
            object_name=object_name,
            data=upload_stream,
            length=len(dummy_image_bytes),
            content_type=TEST_IMAGE_CONTENT_TYPE,
        )

        downloaded_data = real_minio_client.download_bytes(TEST_BUCKET_NAME, object_name)

        assert downloaded_data == dummy_image_bytes
        print(f"✅ Downloaded and verified content for: {object_name}")

    def test_delete_file(self, real_minio_client: MinioClientWrapper, dummy_image_bytes: bytes):
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
        assert "NoSuchKey" in str(excinfo.value) or "Object not found" in str(excinfo.value)
        print(f"✅ Deleted and verified absence of: {object_name}")

    def test_generate_presigned_url(self, real_minio_client: MinioClientWrapper):
        object_name = "test_presigned_url.jpg"

        presigned_url = real_minio_client.generate_presigned_url(TEST_BUCKET_NAME, object_name, expiry_seconds=60)

        assert isinstance(presigned_url, str)
        assert presigned_url.startswith(f"http://{TEST_MINIO_ENDPOINT}/{TEST_BUCKET_NAME}/{object_name}")
        print(f"✅ Generated presigned URL for: {object_name}")
