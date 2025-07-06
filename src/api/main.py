from fastapi import FastAPI

from src.api.routers import beer_cap_router

app = FastAPI(title="Beer Cap API")

app.include_router(beer_cap_router.router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
