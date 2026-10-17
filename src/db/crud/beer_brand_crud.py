from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.schemas.beer_brand.beer_brand_update import BeerBrandUpdateSchema
from src.db.entities.beer_brand_entity import BeerBrand
from src.db.entities.beer_entity import Beer


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
    """Retrieves a single beer brand by its name, ignoring case."""
    stmt = select(BeerBrand).where(func.lower(BeerBrand.name) == func.lower(name))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_all_beer_brands(
    session: AsyncSession, load_beers: bool = False
) -> list[BeerBrand]:
    stmt = select(BeerBrand)
    if load_beers:
        stmt = stmt.options(selectinload(BeerBrand.beers))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_beers_by_brand(session: AsyncSession) -> dict[int, int]:
    """Number of beers of each brand; brands without beers are left out."""
    result = await session.execute(
        select(Beer.beer_brand_id, func.count()).group_by(Beer.beer_brand_id)
    )
    return dict(result.tuples().all())


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

    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(beer_brand, field, value)

    await session.commit()
    await session.refresh(beer_brand)
    return beer_brand
