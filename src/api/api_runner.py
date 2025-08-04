import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.middleware.http_request_logging_middleware import LogRequestMiddleware
from src.api.routers import augmented_cap_router, beer_cap_router, beer_router, similarity_router
from src.utils.logger import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)

app = FastAPI(title="Beer Cap API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.router.redirect_slashes = True

app.include_router(beer_cap_router.router)
app.include_router(beer_router.router)
app.include_router(augmented_cap_router.router)
app.include_router(similarity_router.router)

app.add_middleware(LogRequestMiddleware)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
