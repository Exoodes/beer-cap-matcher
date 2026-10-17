from typing import TYPE_CHECKING, Annotated, Any

from fastapi import Depends, HTTPException, Request, status

# The ML services pull in torch/CLIP/FAISS on import, so they are only
# imported for type checking; at runtime they exist only when matching is on.
if TYPE_CHECKING:
    from src.services.cap_detection_service import CapDetectionService
    from src.services.query_service import QueryService

MATCHING_DISABLED_DETAIL = (
    "Image matching is disabled on this server (set ENABLE_MATCHING=true)."
)


def _require_service(request: Request, name: str) -> Any:
    service = getattr(request.app.state, name, None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=MATCHING_DISABLED_DETAIL,
        )
    return service


def get_query_service(request: Request) -> "QueryService":
    """Gets the query service from the application state.

    Args:
        request: The request object.

    Returns:
        The query service instance.

    Raises:
        HTTPException: 503 if image matching is disabled.
    """
    return _require_service(request, "query_service")


def get_cap_detection_service(request: Request) -> "CapDetectionService":
    """Gets the cap detection service from the application state.

    Args:
        request: The incoming request object.

    Returns:
        An instance of the cap detection service.

    Raises:
        HTTPException: 503 if image matching is disabled.
    """
    return _require_service(request, "cap_detection_service")


async def reload_query_service_index(request: Request) -> None:
    """Reloads the query service index.

    Args:
        request: The incoming request object.
    """
    await get_query_service(request).load_index()


if TYPE_CHECKING:
    QueryServiceDep = Annotated[QueryService, Depends(get_query_service)]
    CapDetectionServiceDep = Annotated[
        CapDetectionService, Depends(get_cap_detection_service)
    ]
else:
    QueryServiceDep = Annotated[Any, Depends(get_query_service)]
    CapDetectionServiceDep = Annotated[Any, Depends(get_cap_detection_service)]
