import logging
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("uvicorn.access")


class LogRequestMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests.
    This middleware intercepts each incoming request, times its processing,
    and logs relevant information after the response is generated. The log
    entry includes the HTTP method, URL path, client host, query parameters,
    response status code, and the total duration of the request-response cycle.

    Attributes:
        dispatch: The main method that processes the request and logs the details.
    """

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        client = request.client.host
        content_type = request.headers.get("content-type", "")
        query_params = dict(request.query_params)

        # Just identify body type — don't consume it
        body_info = "<not logged>"
        if content_type.startswith("application/json"):
            try:
                body_bytes = await request.body()
                request._body = body_bytes  # Patch back
                body_info = body_bytes.decode("utf-8")
            except Exception:
                body_info = "<unreadable JSON body>"

        elif content_type.startswith("multipart/form-data"):
            body_info = "<multipart/form-data - skipped>"

        else:
            body_info = f"<content-type: {content_type}>"

        response = await call_next(request)
        duration = time.time() - start_time

        logger.info(
            f"{request.method} {request.url.path} from {client} "
            f"query={query_params} body={body_info} "
            f"status={response.status_code} duration={duration:.3f}s"
        )

        return response
