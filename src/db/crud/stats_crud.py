"""Counts over the whole collection, computed in SQL."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.entities.beer_cap_entity import BeerCap
from src.db.entities.beer_entity import Beer

NEWEST_COUNT = 5


@dataclass
class CollectionStats:
    caps: int
    beers: int
    brands: int
    countries: int
    collected_this_month: int
    # (month "YYYY-MM", running total), every month from the first to `today`'s.
    growth: list[tuple[str, int]]
    undated: int
    newest: list[BeerCap]
    cap_ids: list[int]


def _month(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _next_month(d: date) -> date:
    return date(d.year + d.month // 12, d.month % 12 + 1, 1)


def running_totals(per_month: dict[str, int], today: date) -> list[tuple[str, int]]:
    """The running total for every month from the first in `per_month` to
    `today`'s; months without caps repeat the total. Empty without caps."""
    if not per_month:
        return []

    def first_of(m: str) -> date:
        return date(int(m[:4]), int(m[5:]), 1)

    month = first_of(min(per_month))
    # A collected date after today still gets its month.
    last = max(date(today.year, today.month, 1), first_of(max(per_month)))
    totals: list[tuple[str, int]] = []
    total = 0
    while month <= last:
        total += per_month.get(_month(month), 0)
        totals.append((_month(month), total))
        month = _next_month(month)
    return totals


async def get_collection_stats(db: AsyncSession, today: date) -> CollectionStats:
    """Beers, brands and countries count only those with a cap, so a row
    left without caps doesn't inflate them. `today` decides "this month"."""
    caps = await db.scalar(select(func.count(BeerCap.id))) or 0
    beers, brands, countries = (
        await db.execute(
            select(
                func.count(distinct(Beer.id)),
                func.count(distinct(Beer.beer_brand_id)),
                func.count(distinct(Beer.country_id)),
            ).join(BeerCap, BeerCap.beer_id == Beer.id)
        )
    ).one()

    month = func.to_char(BeerCap.collected_date, "YYYY-MM")
    per_month = {
        m: n
        for m, n in (
            await db.execute(
                select(month, func.count(BeerCap.id))
                .where(BeerCap.collected_date.is_not(None))
                .group_by(month)
            )
        ).all()
    }
    undated = (
        await db.scalar(
            select(func.count(BeerCap.id)).where(BeerCap.collected_date.is_(None))
        )
        or 0
    )

    newest = list(
        (
            await db.scalars(
                select(BeerCap)
                .options(selectinload(BeerCap.beer))
                .order_by(BeerCap.id.desc())
                .limit(NEWEST_COUNT)
            )
        ).all()
    )
    cap_ids = list((await db.scalars(select(BeerCap.id).order_by(BeerCap.id))).all())

    return CollectionStats(
        caps=caps,
        beers=beers,
        brands=brands,
        countries=countries,
        collected_this_month=per_month.get(_month(today), 0),
        growth=running_totals(per_month, today),
        undated=undated,
        newest=newest,
        cap_ids=cap_ids,
    )
