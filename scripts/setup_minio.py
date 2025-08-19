import asyncio

from src.config.settings import settings
from src.storage.minio.minio_client import MinioClientWrapper


async def ensure_buckets_exist() -> None:
    """Ensures that the required MinIO buckets exist.

    Loads environment variables from a .env file and checks for the presence
    of bucket-related variables. It then uses a Minio client to create these
    buckets if they do not already exist.

    Raises:
        ValueError: If any of the required bucket environment variables are not set.
    """
    buckets = [
        settings.minio_original_caps_bucket,
        settings.minio_augmented_caps_bucket,
        settings.minio_augmented_caps_bucket,
    ]

    if not all(buckets):
        raise ValueError(
            "One or more required MINIO_*_BUCKET environment variables are not set."
        )

    minio_wrapper = MinioClientWrapper()
    minio_wrapper.ensure_buckets_exist(buckets)


if __name__ == "__main__":
    asyncio.run(ensure_buckets_exist())
