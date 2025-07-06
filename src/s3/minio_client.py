# src/s3/minio_client.py

import os
from datetime import timedelta
from typing import BinaryIO, Optional

from minio import Minio
from minio.error import S3Error

from src.utils.logger import get_logger

logger = get_logger(__name__)


class MinioClientWrapper:
    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        secure: Optional[bool] = None,
    ):
        MINIO_ENDPOINT = endpoint if endpoint is not None else os.getenv("MINIO_ENDPOINT", "localhost:9000")
        MINIO_ACCESS_KEY = access_key if access_key is not None else os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        MINIO_SECRET_KEY = secret_key if secret_key is not None else os.getenv("MINIO_SECRET_KEY", "minioadmin")
        MINIO_SECURE = secure if secure is not None else (os.getenv("MINIO_SECURE", "false").lower() == "true")

        self.client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE,
        )

    def upload_file(
        self, bucket_name: str, object_name: str, data: BinaryIO, length: int, content_type: str = "image/png"
    ) -> str:
        try:
            self.client.put_object(
                bucket_name=bucket_name, object_name=object_name, data=data, length=length, content_type=content_type
            )
            logger.info(f"Uploaded {object_name} to {bucket_name}.")
            return object_name
        except S3Error as e:
            logger.error(f"Failed to upload {object_name} to {bucket_name}: {e}")
            raise

    def delete_file(self, bucket_name: str, object_name: str) -> None:
        try:
            self.client.remove_object(bucket_name, object_name)
            logger.info(f"Deleted {object_name} from {bucket_name}.")
        except S3Error as e:
            logger.error(f"Failed to delete {object_name} from {bucket_name}: {e}")
            raise

    def download_bytes(self, bucket_name: str, object_name: str) -> bytes:
        response = None
        try:
            response = self.client.get_object(bucket_name, object_name)
            data = response.read()
            logger.info(f"Downloaded {object_name} from {bucket_name}.")
            return data
        except S3Error as e:
            logger.error(f"Failed to download {object_name} from {bucket_name}: {e}")
            raise
        finally:
            if response:
                response.close()
                response.release_conn()

    def generate_presigned_url(self, bucket_name: str, object_name: str, expiry_seconds=3600) -> str:
        try:
            url = self.client.presigned_get_object(bucket_name, object_name, expires=timedelta(seconds=expiry_seconds))
            logger.info(f"Generated presigned URL for {object_name} in {bucket_name}.")
            return url
        except S3Error as e:
            logger.error(f"Failed to generate presigned URL for {object_name} in {bucket_name}: {e}")
            raise

    def ensure_buckets_exist(self, buckets: list[str]) -> None:
        for bucket in buckets:
            found = self.client.bucket_exists(bucket)
            if not found:
                self.client.make_bucket(bucket)
                logger.info(f"Created bucket: {bucket}")
            else:
                logger.info(f"Bucket already exists: {bucket}")
