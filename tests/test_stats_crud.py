from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.beer_cap.beer_cap_create import BeerCapCreateSchema
from src.api.schemas.country.country_create import CountryCreateSchema
from src.db.crud.beer_brand_crud import create_beer_brand
from src.db.crud.beer_cap_crud import create_beer_cap
from src.db.crud.beer_crud import create_beer
from src.db.crud.country_crud import create_country
from src.db.crud.stats_crud import get_collection_stats, running_totals

TODAY = date(2026, 10, 23)


def test_running_totals_fill_gap_months_up_to_today() -> None:
    assert running_totals({"2026-07": 2, "2026-09": 3}, TODAY) == [
        ("2026-07", 2),
        ("2026-08", 2),
        ("2026-09", 5),
        ("2026-10", 5),
    ]
    assert running_totals({}, TODAY) == []
    # Across a year end, and a date after today keeps its month.
    assert running_totals({"2025-12": 1, "2026-01": 1}, date(2025, 12, 5)) == [
        ("2025-12", 1),
        ("2026-01", 2),
    ]


@pytest.mark.asyncio
async def test_empty_collection(db_session: AsyncSession) -> None:
    stats = await get_collection_stats(db_session, TODAY)
    assert (stats.caps, stats.beers, stats.brands, stats.countries) == (0, 0, 0, 0)
    assert stats.collected_this_month == 0
    assert stats.growth == []
    assert stats.undated == 0
    assert stats.newest == []
    assert stats.cap_ids == []


@pytest.mark.asyncio
async def test_counts_growth_and_newest(db_session: AsyncSession) -> None:
    czechia = await create_country(db_session, CountryCreateSchema(name="Czechia"))
    # A country and a brand without caps don't count.
    await create_country(db_session, CountryCreateSchema(name="Empty"))
    await create_beer_brand(db_session, "No Caps Brewery")
    brand = await create_beer_brand(db_session, "Kozel")
    beer_a = await create_beer(db_session, "Kozel 11", brand.id, country_id=czechia.id)
    beer_b = await create_beer(db_session, "Kozel 10", brand.id)  # no country
    await create_beer(db_session, "Kozel Dark", brand.id)  # no caps

    async def cap(beer_id: int, key: str, collected: date | None) -> int:
        created = await create_beer_cap(
            db_session,
            beer_id,
            key,
            BeerCapCreateSchema(filename=key, collected_date=collected),
        )
        return created.id

    ids = [
        await cap(beer_a.id, "a.jpg", date(2026, 1, 1)),
        await cap(beer_a.id, "b.jpg", date(2026, 1, 1)),
        await cap(beer_b.id, "c.jpg", date(2026, 9, 26)),
        await cap(beer_b.id, "d.jpg", date(2026, 10, 2)),
        await cap(beer_b.id, "e.jpg", None),
        await cap(beer_a.id, "f.jpg", date(2025, 3, 1)),
    ]

    stats = await get_collection_stats(db_session, TODAY)
    assert (stats.caps, stats.beers, stats.brands, stats.countries) == (6, 2, 1, 1)
    assert stats.collected_this_month == 1
    assert stats.undated == 1
    assert stats.growth[0] == ("2025-03", 1)
    assert stats.growth[-1] == ("2026-10", 5)
    assert len(stats.growth) == 20  # Mar 2025 to Oct 2026
    # Newest by entry order (id), not by collected date.
    assert [c.id for c in stats.newest] == ids[::-1][:5]
    assert stats.newest[0].beer.name == "Kozel 11"
    assert stats.cap_ids == ids
