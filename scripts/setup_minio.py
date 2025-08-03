import asyncio

from src.storage.minio.minio_client import MinioClientWrapper


async def ensure_buckets_exist():
    buckets = ["beer-caps", "augmented-caps", "faiss-index"]
    minio_wrapper = MinioClientWrapper()
    minio_wrapper.ensure_buckets_exist(buckets)


if __name__ == "__main__":
    asyncio.run(ensure_buckets_exist())
