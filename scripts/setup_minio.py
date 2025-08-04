import asyncio
import os

from dotenv import load_dotenv

from src.storage.minio.minio_client import MinioClientWrapper


async def ensure_buckets_exist() -> None:
    """Ensures that the required MinIO buckets exist.

    Loads environment variables from a .env file and checks for the presence
    of bucket-related variables. It then uses a Minio client to create these
    buckets if they do not already exist.

    Raises:
        ValueError: If any of the required bucket environment variables are not set.
    """
    load_dotenv()

    bucket_env_vars = [
        "MINIO_ORIGINAL_CAPS_BUCKET",
        "MINIO_AUGMENTED_CAPS_BUCKET",
        "MINIO_INDEX_BUCKET",
    ]

    buckets = []
    for var in bucket_env_vars:
        value = os.getenv(var)
        if value is None:
            raise ValueError(f"Error: Environment variable '{var}' is not set.")
        buckets.append(value)

    minio_wrapper = MinioClientWrapper()
    minio_wrapper.ensure_buckets_exist(buckets)


if __name__ == "__main__":
    asyncio.run(ensure_buckets_exist())
