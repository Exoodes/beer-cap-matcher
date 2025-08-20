import concurrent.futures
import os
from datetime import timedelta
from typing import BinaryIO, Optional
from urllib.parse import urlparse

from minio import Minio
from minio.deleteobjects import DeleteObject
from minio.error import S3Error

from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MinioClientWrapper:
    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        secure: Optional[bool] = None,
    ) -> None:
        raw = (endpoint if endpoint is not None else settings.minio_endpoint).strip()

        # Normalize: add scheme if missing so urlparse works consistently
        parsed = urlparse(raw if "://" in raw else f"http://{raw}")

        # If a path sneaks in (including trailing "/"), strip it but WARN so you can fix envs
        if parsed.path and parsed.path != "":
            logger.warning(
                "MINIO_ENDPOINT contained a path '%s' -> stripping it. Raw: %r",
                parsed.path,
                raw,
            )

        host = parsed.hostname or ""
        port = (
            f":{parsed.port}"
            if parsed.port
            else (f":{parsed.netloc.split(':',1)[1]}" if ":" in parsed.netloc else "")
        )
        hostport = f"{host}{port}" if host else (parsed.netloc or raw.split("/", 1)[0])

        # Decide secure: prefer scheme if present, otherwise use provided flag/env
        secure_flag = (
            (parsed.scheme == "https")
            if parsed.scheme
            else (secure if secure is not None else settings.minio_secure)
        )

        logger.info(
            "Initializing MinIO client with endpoint=%r (normalized=%r), secure=%s",
            raw,
            hostport,
            secure_flag,
        )

        self.client = Minio(
            hostport,
            access_key=access_key or settings.minio_access_key,
            secret_key=secret_key or settings.minio_secret_key,
            secure=secure_flag,
        )

    def upload_file(
        self,
        bucket_name: str,
        object_name: str,
        data: BinaryIO,
        length: Optional[int] = None,
        content_type: str = "image/png",
    ) -> str:
        """Uploads a file to a specified bucket.

        Args:
            bucket_name (str): Name of the bucket.
            object_name (str): Key (path) to store the object under.
            data (BinaryIO): File-like object with the data to upload.
            length (Optional[int]): Size of the object in bytes. If None, it will be computed.
            content_type (str): MIME type of the object.

        Returns:
            str: The name of the uploaded object.

        Raises:
            ValueError: If length is not provided and cannot be determined.
            S3Error: If the upload fails.
        """
        try:
            if length is None:
                if hasattr(data, "seek") and hasattr(data, "tell"):
                    current_pos = data.tell()
                    data.seek(0, os.SEEK_END)
                    length = data.tell()
                    data.seek(current_pos)
                else:
                    raise ValueError(
                        "Cannot determine length of non-seekable stream. Please provide length."
                    )

            self.client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=data,
                length=length,
                content_type=content_type,
            )
            logger.info("Uploaded %s to %s.", object_name, bucket_name)
            return object_name
        except (S3Error, ValueError) as e:
            logger.error("Failed to upload %s to %s: %s", object_name, bucket_name, e)
            raise

    def delete_file(self, bucket_name: str, object_name: str) -> None:
        """Deletes an object from a specified bucket.

        Args:
            bucket_name (str): Name of the bucket.
            object_name (str): Name of the object to delete.

        Raises:
            S3Error: If the deletion fails.
        """
        try:
            self.client.remove_object(bucket_name, object_name)
            logger.info("Deleted %s from %s.", object_name, bucket_name)
        except S3Error as e:
            logger.error("Failed to delete %s from %s: %s", object_name, bucket_name, e)
            raise

    def delete_files(self, bucket_name: str, object_names: list[str]) -> None:
        """Deletes multiple objects from a bucket in a single batch.

        Args:
            bucket_name (str): Name of the bucket.
            object_names (list[str]): List of object keys to delete.

        Raises:
            S3Error: If the deletion fails.
        """
        try:
            delete_objects = [DeleteObject(name) for name in object_names]
            errors = self.client.remove_objects(bucket_name, delete_objects)
            for error in errors:
                logger.error(
                    "Failed to delete %s from %s: %s",
                    error.name,
                    bucket_name,
                    error.message,
                )
        except S3Error as e:
            logger.error("Failed to delete objects from %s: %s", bucket_name, e)
            raise

    def object_exists(self, bucket_name: str, object_name: str) -> bool:
        """Checks if an object exists in the specified bucket.

        Args:
            bucket_name (str): Name of the bucket.
            object_name (str): Name of the object to check.

        Returns:
            bool: True if the object exists, False otherwise.
        """
        try:
            self.client.stat_object(bucket_name, object_name)
            logger.info("Object %s exists in bucket %s.", object_name, bucket_name)
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                logger.info(
                    "Object %s does not exist in bucket %s.", object_name, bucket_name
                )
                return False
            logger.error(
                "Error checking existence of %s in %s: %s", object_name, bucket_name, e
            )
            return False

    def download_bytes(self, bucket_name: str, object_name: str) -> bytes:
        """Downloads an object from a bucket and returns its content as bytes.

        Args:
            bucket_name (str): Name of the bucket.
            object_name (str): Name of the object to download.

        Returns:
            bytes: Contents of the object.

        Raises:
            S3Error: If the download fails.
        """
        response = None
        try:
            response = self.client.get_object(bucket_name, object_name)
            data = response.read()
            logger.info("Downloaded %s from %s.", object_name, bucket_name)
            return data
        except S3Error as e:
            logger.error(
                "Failed to download %s from %s: %s", object_name, bucket_name, e
            )
            raise
        finally:
            if response:
                response.close()
                response.release_conn()

    def generate_presigned_url(
        self, bucket_name: str, object_name: str, expiry_seconds: int = 3600
    ) -> str:
        """Generates a presigned URL for temporary access to an object.

        Args:
            bucket_name (str): Name of the bucket.
            object_name (str): Name of the object.
            expiry_seconds (int): Time in seconds until the URL expires.

        Returns:
            str: The presigned URL.

        Raises:
            S3Error: If URL generation fails.
        """
        try:
            url = self.client.presigned_get_object(
                bucket_name, object_name, expires=timedelta(seconds=expiry_seconds)
            )
            logger.info(
                "Generated presigned URL for %s in %s.", object_name, bucket_name
            )
            return url
        except S3Error as e:
            logger.error(
                "Failed to generate presigned URL for %s in %s: %s",
                object_name,
                bucket_name,
                e,
            )
            raise

    def ensure_buckets_exist(self, buckets: list[str]) -> None:
        """Ensures that the specified buckets exist. Creates them if they don't.

        Args:
            buckets (list[str]): List of bucket names to ensure exist.
        """
        for bucket in buckets:
            found = self.client.bucket_exists(bucket)
            if not found:
                self.client.make_bucket(bucket)
                logger.info("Created bucket: %s", bucket)
            else:
                logger.info("Bucket already exists: %s", bucket)

    def download_all_objects_parallel(
        self,
        bucket_name: str,
        prefix: str = "",
        recursive: bool = True,
        max_workers: int = 8,
    ) -> list[tuple[str, bytes]]:
        """Downloads all objects from a bucket in parallel and returns their contents.

        Args:
            bucket_name (str): Name of the bucket to download from.
            prefix (str, optional): Prefix to filter objects. Defaults to "".
            recursive (bool, optional): Whether to list objects recursively. Defaults to True.
            max_workers (int, optional): Number of parallel download threads. Defaults to 8.

        Returns:
            list[tuple[str, bytes]]: A list of (object_name, object_data) tuples.
        """
        object_names = [
            obj.object_name
            for obj in self.client.list_objects(
                bucket_name, prefix=prefix, recursive=recursive
            )
        ]

        def download_object(name: str) -> tuple[str, bytes]:
            try:
                response = self.client.get_object(bucket_name, name)
                data = response.read()
                response.close()
                response.release_conn()
                logger.info("Downloaded %s from %s.", name, bucket_name)
                return name, data
            except S3Error as e:
                logger.error("Failed to download %s: %s", name, e)
                return name, b""

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_name = {
                executor.submit(download_object, name): name for name in object_names
            }
            for future in concurrent.futures.as_completed(future_to_name):
                result = future.result()
                if result[1]:
                    results.append(result)

        return results
