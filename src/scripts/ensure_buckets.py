from src.s3.minio_client import minio_client


async def ensure_buckets_exist():
    buckets = ["beer-caps", "augmented-caps"]

    for bucket in buckets:
        found = minio_client.bucket_exists(bucket)
        if not found:
            minio_client.make_bucket(bucket)
            print(f"✅ Created bucket: {bucket}")
        else:
            print(f"ℹ️ Bucket already exists: {bucket}")
