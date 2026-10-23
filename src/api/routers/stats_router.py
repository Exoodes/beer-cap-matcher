from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.constants.responses import INTERNAL_SERVER_ERROR_RESPONSE
from src.api.dependencies.db import get_db_session
from src.api.dependencies.facades import get_beer_cap_facade
from src.api.schemas.stats.stats_response import (
    GrowthPoint,
    NewestCap,
    StatsResponse,
)
from src.db.crud.stats_crud import get_collection_stats
from src.services.beer_cap_facade import BeerCapFacade
from src.utils.dates import today_local

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get(
    "/",
    response_model=StatsResponse,
    responses=INTERNAL_SERVER_ERROR_RESPONSE,
)
async def get_stats(
    beer_cap_facade: BeerCapFacade = Depends(get_beer_cap_facade),
    db: AsyncSession = Depends(get_db_session),
) -> StatsResponse:
    """
    Counts over the whole collection (for the home dashboard): totals, caps
    collected this month, growth by month, the newest caps and every cap's ID.
    Public like the other reads: it shows nothing they don't.
    """
    stats = await get_collection_stats(db, today_local())
    return StatsResponse(
        caps=stats.caps,
        beers=stats.beers,
        brands=stats.brands,
        countries=stats.countries,
        collected_this_month=stats.collected_this_month,
        growth=[GrowthPoint(month=m, total=t) for m, t in stats.growth],
        undated=stats.undated,
        newest=[
            NewestCap(
                id=cap.id,
                beer=cap.beer.name,
                thumbnail_url=beer_cap_facade.get_image_url(
                    cap.thumbnail_s3_key or cap.s3_key
                ),
            )
            for cap in stats.newest
        ],
        cap_ids=stats.cap_ids,
    )
