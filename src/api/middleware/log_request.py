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

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        query_params = dict(request.query_params)
        client = request.client.host

        logger.info(
            "%s %s from %s query=%s status=%s duration=%.3fs",
            request.method,
            request.url.path,
            client,
            query_params,
            response.status_code,
            duration,
        )

        return response
