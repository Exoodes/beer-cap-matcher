from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.schemas.beer_brand.beer_brand_update import BeerBrandUpdateSchema
from src.db.entities.beer_brand_entity import BeerBrand


async def create_beer_brand(
    session: AsyncSession, name: str, commit: bool = True
) -> BeerBrand:
    beer_brand = BeerBrand(name=name)
    session.add(beer_brand)

    if commit:
        await session.commit()
    else:
        await session.flush()

    await session.refresh(beer_brand)
    return beer_brand


async def get_beer_brand_by_id(
    session: AsyncSession, beer_brand_id: int, load_beers: bool = False
) -> Optional[BeerBrand]:
    stmt = select(BeerBrand).where(BeerBrand.id == beer_brand_id)
    if load_beers:
        stmt = stmt.options(selectinload(BeerBrand.beers))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_beer_brand_by_name(
    session: AsyncSession, name: str
) -> Optional[BeerBrand]:
    """Retrieves a single beer brand by its name."""
    stmt = select(BeerBrand).where(BeerBrand.name == name)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_all_beer_brands(
    session: AsyncSession, load_beers: bool = False
) -> List[BeerBrand]:
    stmt = select(BeerBrand)
    if load_beers:
        stmt = stmt.options(selectinload(BeerBrand.beers))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def delete_beer_brand(session: AsyncSession, beer_brand_id: int) -> bool:
    beer_brand = await get_beer_brand_by_id(session, beer_brand_id)
    if beer_brand:
        await session.delete(beer_brand)
        await session.commit()
    return beer_brand is not None


async def update_beer_brand(
    session: AsyncSession,
    beer_brand_id: int,
    update_data: BeerBrandUpdateSchema,
    load_beers: bool = False,
) -> Optional[BeerBrand]:
    stmt = select(BeerBrand).where(BeerBrand.id == beer_brand_id)
    if load_beers:
        stmt = stmt.options(selectinload(BeerBrand.beers))
    result = await session.execute(stmt)
    beer_brand = result.scalar_one_or_none()
    if not beer_brand:
        return None

    if update_data.name is not None:
        beer_brand.name = update_data.name

    await session.commit()
    await session.refresh(beer_brand)
    return beer_brand
