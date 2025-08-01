from src.storage.minio_client import MinioClientWrapper


def get_minio_client():
    return MinioClientWrapper()
