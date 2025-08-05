from fastapi import Request

from src.services.cap_detection_service import CapDetectionService
from src.services.query_service import QueryService


def get_query_service(request: Request) -> QueryService:
    """Gets the query service from the application state.

    Args:
        request: The request object.

    Returns:
        The query service instance.
    """
    return request.app.state.query_service


def get_cap_detection_service(request: Request) -> CapDetectionService:
    """Gets the cap detection service from the application state.

    Args:
        request: The incoming request object.

    Returns:
        An instance of the cap detection service.
    """
    return request.app.state.cap_detection_service


async def reload_query_service_index(request: Request) -> None:
    """Reloads the query service index.

    Args:
        request: The incoming request object.
    """
    await request.app.state.query_service.load_index()
