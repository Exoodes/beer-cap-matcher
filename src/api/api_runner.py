from contextlib import asynccontextmanager
from typing import Any, Generator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.api.middleware.http_request_logging_middleware import LogRequestMiddleware
from src.api.routers import augmented_cap_router, beer_brand_router, beer_cap_router, beer_router, similarity_router
from src.services.cap_detection_service import CapDetectionService
from src.services.query_service import QueryService
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

    # Initialize services
    minio_client = MinioClientWrapper()
    query_service = QueryService(minio_wrapper=minio_client)
    await query_service.load_index()
    cap_detection_service = CapDetectionService(minio_wrapper=minio_client)

    app.state.minio_client = minio_client
    app.state.query_service = query_service
    app.state.cap_detection_service = cap_detection_service

    logger.info("Services initialized.")
    yield
    logger.info("Shutting down app.")


app = FastAPI(title="Beer Cap API", lifespan=lifespan)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LogRequestMiddleware)

# Routers
app.include_router(beer_cap_router.router)
app.include_router(beer_router.router)
app.include_router(augmented_cap_router.router)
app.include_router(similarity_router.router)
app.include_router(beer_brand_router.router)

app.router.redirect_slashes = True

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
