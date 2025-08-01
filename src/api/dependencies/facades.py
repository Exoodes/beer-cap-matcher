from fastapi import Depends

from src.api.dependencies.minio import get_minio_client
from src.facades.beer_cap_facade import BeerCapFacade
from src.storage.minio_client import MinioClientWrapper


def get_beer_cap_facade(minio_client: MinioClientWrapper = Depends(get_minio_client)):
    return BeerCapFacade(minio_wrapper=minio_client)
