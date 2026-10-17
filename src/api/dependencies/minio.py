from fastapi import Request

from src.storage.minio.minio_client import MinioClientWrapper


def get_minio_client(request: Request) -> MinioClientWrapper:
    """Gets the shared Minio client wrapper created at application startup.

    Args:
        request: The incoming request object.

    Returns:
        MinioClientWrapper: The application-wide Minio client wrapper.
    """
    return request.app.state.minio_client
