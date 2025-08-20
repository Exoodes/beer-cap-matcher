"""Custom middleware used by the FastAPI application."""

from .http_request_logging_middleware import LogRequestMiddleware

__all__ = ["LogRequestMiddleware"]
