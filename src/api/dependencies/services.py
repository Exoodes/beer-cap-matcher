from fastapi import Depends

from src.api.dependencies.minio import get_minio_client
from src.services.cap_detection_service import CapDetectionService
from src.storage.minio.minio_client import MinioClientWrapper


def get_cap_detection_service(minio_client: MinioClientWrapper = Depends(get_minio_client)) -> CapDetectionService:
    """FastAPI dependency for getting the cap detection service.

    Args:
        minio_client (MinioClientWrapper): A Minio client wrapper instance,
            injected by FastAPI's dependency system.

    Returns:
        CapDetectionService: An instance of the CapDetectionService,
            initialized with the Minio client wrapper.
    """
    return CapDetectionService(minio_wrapper=minio_client)
