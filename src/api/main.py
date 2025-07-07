from fastapi import FastAPI

from src.api.routers import augmented_cap_router, beer_cap_router, beer_router

app = FastAPI(title="Beer Cap API")

app.include_router(beer_cap_router.router)
app.include_router(beer_router.router)
app.include_router(augmented_cap_router.router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
