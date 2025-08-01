from fastapi import Depends

from src.api.dependencies.minio import get_minio_client
from src.services.cap_detection_service import CapDetectionService
from src.storage.minio_client import MinioClientWrapper


def get_cap_detection_service(minio_client: MinioClientWrapper = Depends(get_minio_client)):
    """
    Provides a service for beer cap detection operations.
    """
    return CapDetectionService(minio_wrapper=minio_client)
