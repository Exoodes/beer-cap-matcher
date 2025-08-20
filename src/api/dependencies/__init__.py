"""FastAPI dependency providers used by the application."""

from .db import get_db_session
from .facades import get_beer_cap_facade
from .minio import get_minio_client
from .services import (
    get_cap_detection_service,
    get_query_service,
    reload_query_service_index,
)

__all__ = [
    "get_db_session",
    "get_beer_cap_facade",
    "get_minio_client",
    "get_cap_detection_service",
    "get_query_service",
    "reload_query_service_index",
]
