"""Maps domain and database errors to JSON HTTP responses."""

import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from src.services.errors import NotFoundError

logger = logging.getLogger(__name__)

# PostgreSQL SQLSTATE codes
UNIQUE_VIOLATION = "23505"
FOREIGN_KEY_VIOLATION = "23503"


def _sqlstate(exc: IntegrityError) -> str | None:
    orig = exc.orig
    return getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)


async def not_found_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def validation_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """Schemas built inside endpoints raise pydantic errors; report them as 422."""
    assert isinstance(exc, ValidationError)
    errors = exc.errors(include_url=False, include_context=False)
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(errors)})


async def integrity_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, IntegrityError)
    code = _sqlstate(exc)
    if code == UNIQUE_VIOLATION:
        detail = "An item with this name already exists."
    elif code == FOREIGN_KEY_VIOLATION:
        detail = "This item is still used by other records; remove those first."
    else:
        detail = "The change conflicts with existing data."
    logger.info("Integrity error (%s): %s", code, exc.orig)
    return JSONResponse(status_code=409, content={"detail": detail})


class UnhandledErrorMiddleware(BaseHTTPMiddleware):
    """Turns unexpected exceptions into a JSON 500.

    Starlette's default 500 handler runs outside every middleware, so its
    response has no CORS headers and browsers report it as a network error.
    This middleware sits inside CORSMiddleware, so the 500 is readable.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        try:
            return await call_next(request)
        except Exception:
            logger.exception("Unhandled error on %s %s", request.method, request.url)
            return JSONResponse(
                status_code=500, content={"detail": "Internal server error."}
            )


def register_error_handlers(app: FastAPI) -> None:
    """Registers the exception handlers. Add before CORSMiddleware."""
    app.add_exception_handler(NotFoundError, not_found_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_middleware(UnhandledErrorMiddleware)
