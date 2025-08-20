import json
import logging
import time

from fastapi import Request
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
        client_host = request.client.host if request.client else "unknown"
        content_type = request.headers.get("content-type", "")
        query_params = dict(request.query_params)

        body_info = "<not logged>"
        max_body_size = 2048

        if content_type.startswith("application/json"):
            try:
                body_bytes = await request.body()
                request.state.body = body_bytes

                async def receive() -> dict:
                    return {
                        "type": "http.request",
                        "body": body_bytes,
                        "more_body": False,
                    }

                request = Request(request.scope, receive)

                if len(body_bytes) <= max_body_size:
                    body_json = json.loads(body_bytes)
                    sensitive_keys = {"password", "token", "secret"}
                    if sensitive_keys.intersection(body_json.keys()):
                        body_info = "<sensitive data redacted>"
                    else:
                        body_info = json.dumps(body_json)
                else:
                    body_info = "<body too large>"
            except Exception:
                body_info = "<unreadable JSON body>"
        elif content_type.startswith("multipart/form-data"):
            body_info = "<multipart/form-data - skipped>"
        else:
            body_info = f"<content-type: {content_type}>"

        response = await call_next(request)
        duration = time.time() - start_time

        logger.info(
            f"{request.method} {request.url.path} from {client_host} "
            f"query={query_params} body={body_info} "
            f"status={response.status_code} duration={duration:.3f}s"
        )

        return response
