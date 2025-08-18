from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.schemas.beer.beer_update import BeerUpdateSchema
from src.db.entities.beer_entity import Beer


async def create_beer(
    session: AsyncSession,
    name: str,
    beer_brand_id: int,
    rating: int = 0,
    country_id: Optional[int] = None,
    commit: bool = True,
) -> Beer:
    beer = Beer(
        name=name, rating=rating, beer_brand_id=beer_brand_id, country_id=country_id
    )
    session.add(beer)

    if commit:
        await session.commit()
    else:
        await session.flush()

    await session.refresh(beer)
    return beer


async def get_beer_by_id(
    session: AsyncSession,
    beer_id: int,
    load_caps: bool = False,
    load_beer_brand: bool = False,
    load_country: bool = False,
) -> Optional[Beer]:
    stmt = select(Beer).where(Beer.id == beer_id)

    if load_caps:
        stmt = stmt.options(selectinload(Beer.caps))
    if load_country:
        stmt = stmt.options(selectinload(Beer.country))

    if load_beer_brand:
        stmt = stmt.options(selectinload(Beer.beer_brand))

    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_all_beers(
    session: AsyncSession,
    load_caps: bool = False,
    load_country: bool = False,
) -> List[Beer]:
    stmt = select(Beer)

    if load_caps:
        stmt = stmt.options(selectinload(Beer.caps))
    if load_country:
        stmt = stmt.options(selectinload(Beer.country))

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def delete_beer(session: AsyncSession, beer_id: int) -> bool:
    beer = await get_beer_by_id(session, beer_id)

    if beer:
        await session.delete(beer)
        await session.commit()

    return beer is not None


async def update_beer(
    session: AsyncSession,
    beer_id: int,
    update_data: BeerUpdateSchema,
    load_caps: bool = False,
    load_beer_brand: bool = False,
    load_country: bool = False,
) -> Optional[Beer]:
    stmt = select(Beer).where(Beer.id == beer_id)

    if load_caps:
        stmt = stmt.options(selectinload(Beer.caps))
    if load_country:
        stmt = stmt.options(selectinload(Beer.country))

    if load_beer_brand:
        stmt = stmt.options(selectinload(Beer.beer_brand))

    result = await session.execute(stmt)
    beer = result.scalar_one_or_none()

    if not beer:
        return None

    if update_data.name is not None:
        beer.name = update_data.name
    if update_data.rating is not None:
        beer.rating = update_data.rating
    if update_data.beer_brand_id is not None:
        beer.beer_brand_id = update_data.beer_brand_id
    if update_data.country_id is not None:
        beer.country_id = update_data.country_id

    await session.commit()
    await session.refresh(beer)
    return beer
