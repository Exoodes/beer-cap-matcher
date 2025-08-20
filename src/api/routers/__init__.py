"""FastAPI routers exposed by the API package."""

from .augmented_cap_router import router as augmented_cap_router
from .beer_brand_router import router as beer_brand_router
from .beer_cap_router import router as beer_cap_router
from .beer_router import router as beer_router
from .country_router import router as country_router
from .similarity_router import router as similarity_router

__all__ = [
    "augmented_cap_router",
    "beer_brand_router",
    "beer_cap_router",
    "beer_router",
    "country_router",
    "similarity_router",
]
