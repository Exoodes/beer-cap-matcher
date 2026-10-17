import asyncio
from contextlib import asynccontextmanager

import uvicorn
from sqlalchemy import text
from src.config.settings import settings
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.error_handlers import register_error_handlers
from src.api.middleware.http_request_logging_middleware import LogRequestMiddleware
from src.api.routers import (
    augmented_cap_router,
    beer_brand_router,
    beer_cap_router,
    beer_router,
    country_router,
    similarity_router,
    backup_router,
)
from src.db.database import GLOBAL_ASYNC_SESSION_MAKER
from src.storage.minio.minio_client import MinioClientWrapper
from src.utils.logger import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Asynchronous context manager for the FastAPI application's lifespan.

    Args:
        _: The FastAPI application instance (not used).

    Yields:
        The function yields control back to the application, which then
        starts running.
    """
    logger.info("Starting app and initializing services...")

    if not settings.admin_secret_token:
        logger.warning("ADMIN_SECRET_TOKEN is not set; all admin endpoints will 401.")

    app.state.minio_client = MinioClientWrapper()
    app.state.query_service = None
    app.state.cap_detection_service = None

    if settings.enable_matching:
        # Imported here so torch/CLIP/FAISS are only loaded when matching is on.
        from src.services.cap_detection_service import CapDetectionService
        from src.services.query_service import QueryService

        query_service = QueryService(minio_wrapper=app.state.minio_client)
        await query_service.load_index()
        app.state.query_service = query_service
        app.state.cap_detection_service = CapDetectionService(
            minio_wrapper=app.state.minio_client
        )
    else:
        logger.info("Image matching disabled (ENABLE_MATCHING=false).")

    logger.info("Services initialized.")
    yield
    logger.info("Shutting down app.")


app = FastAPI(title="Beer Cap API", lifespan=lifespan)

# Middleware. Error handling goes first so it sits inside CORS.
register_error_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LogRequestMiddleware)

# Routers
app.include_router(beer_cap_router)
app.include_router(beer_router)
app.include_router(country_router)
app.include_router(augmented_cap_router)
app.include_router(similarity_router)
app.include_router(beer_brand_router)
app.include_router(backup_router)


@app.get("/health", tags=["health"])
async def health(request: Request) -> JSONResponse:
    """Health check: verifies the database and object storage are reachable.

    Returns 200 when both are up, otherwise 503 with the failing checks.
    """
    checks: dict[str, str] = {}

    try:
        async with GLOBAL_ASYNC_SESSION_MAKER() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        logger.warning("Health check: database unavailable: %s", e)
        checks["database"] = "error"

    try:
        minio_client: MinioClientWrapper = request.app.state.minio_client
        bucket_ok = await asyncio.to_thread(
            minio_client.client.bucket_exists, settings.minio_original_caps_bucket
        )
        checks["storage"] = "ok" if bucket_ok else "error"
    except Exception as e:
        logger.warning("Health check: storage unavailable: %s", e)
        checks["storage"] = "error"

    healthy = all(v == "ok" for v in checks.values())
    query_service = request.app.state.query_service
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={
            "status": "ok" if healthy else "error",
            "checks": checks,
            "matching": {
                "enabled": settings.enable_matching,
                "index_loaded": bool(query_service and query_service.querier),
            },
        },
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
