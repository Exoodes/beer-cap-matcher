from src.storage.minio.minio_client import MinioClientWrapper


def get_minio_client():
    return MinioClientWrapper()
