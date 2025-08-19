from fastapi import Depends

from src.api.dependencies.minio import get_minio_client
from src.services.beer_cap_facade import BeerCapFacade
from src.storage.minio.minio_client import MinioClientWrapper


def get_beer_cap_facade(
    minio_client: MinioClientWrapper = Depends(get_minio_client),
) -> BeerCapFacade:
    """FastAPI dependency to get a `BeerCapFacade` instance.

    Args:
        minio_client (MinioClientWrapper): An initialized Minio client wrapper,
            injected by FastAPI's dependency system.

    Returns:
        BeerCapFacade: An instance of the `BeerCapFacade` initialized with the
            Minio client.
    """
    return BeerCapFacade(minio_wrapper=minio_client)
