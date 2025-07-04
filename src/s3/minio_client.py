import os

from minio import Minio

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE,
)


def upload_bytes(bucket_name: str, object_name: str, data: bytes, content_type: str = "image/png"):
    minio_client.put_object(
        bucket_name=bucket_name,
        object_name=object_name,
        data=data,
        length=len(data),
        content_type=content_type,
    )


def download_bytes(bucket_name: str, object_name: str) -> bytes:
    response = minio_client.get_object(bucket_name, object_name)
    data = response.read()
    response.close()
    response.release_conn()
    return data


def generate_presigned_url(bucket_name: str, object_name: str, expires=3600) -> str:
    return minio_client.presigned_get_object(bucket_name, object_name, expires=expires)
