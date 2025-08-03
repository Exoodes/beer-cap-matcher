from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import augmented_cap_router, beer_cap_router, beer_router, similarity_router

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

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
