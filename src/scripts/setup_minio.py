import asyncio

from src.s3.minio_client import MinioClientWrapper


async def ensure_buckets_exist():
    buckets = ["beer-caps", "augmented-caps"]
    minio_wrapper = MinioClientWrapper()
    minio_wrapper.ensure_buckets_exist(buckets)


if __name__ == "__main__":
    asyncio.run(ensure_buckets_exist())
