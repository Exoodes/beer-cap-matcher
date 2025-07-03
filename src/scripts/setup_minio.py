import asyncio

from src.scripts.ensure_buckets import ensure_buckets_exist

if __name__ == "__main__":
    asyncio.run(ensure_buckets_exist())
