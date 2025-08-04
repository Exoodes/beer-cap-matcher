from fastapi import Depends

from src.api.dependencies.minio import get_minio_client
from src.services.cap_detection_service import CapDetectionService
from src.storage.minio.minio_client import MinioClientWrapper

_cap_detection_service: CapDetectionService | None = None


async def get_cap_detection_service(
    minio_client: MinioClientWrapper = Depends(get_minio_client),
) -> CapDetectionService:
    """FastAPI dependency for getting the cap detection service.

    Args:
        minio_client (MinioClientWrapper): A Minio client wrapper instance,
            injected by FastAPI's dependency system.

    Returns:
        CapDetectionService: An instance of the CapDetectionService,
            initialized with the Minio client wrapper.
    """
    global _cap_detection_service
    if _cap_detection_service is None:
        _cap_detection_service = CapDetectionService(minio_wrapper=minio_client)
        await _cap_detection_service.load_index()

    return _cap_detection_service


def reload_cap_detection_service_index() -> None:
    global _cap_detection_service
    if _cap_detection_service:
        _cap_detection_service.load_index()
