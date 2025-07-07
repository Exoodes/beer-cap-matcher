from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.entities.beer_cap import BeerCap


async def create_beer_cap(session: AsyncSession, beer_id: int, s3_key: str, commit: bool = True) -> BeerCap:
    new_cap = BeerCap(beer_id=beer_id, s3_key=s3_key)
    session.add(new_cap)

    if commit:
        await session.commit()
    else:
        await session.flush()

    await session.refresh(new_cap)
    return new_cap


async def get_beer_cap_by_id(
    session: AsyncSession,
    beer_cap_id: int,
    load_augmented_caps: bool = False,
    load_beer: bool = False,
) -> Optional[BeerCap]:
    stmt = select(BeerCap).where(BeerCap.id == beer_cap_id)

    if load_augmented_caps:
        stmt = stmt.options(selectinload(BeerCap.augmented_caps))
    if load_beer:
        stmt = stmt.options(selectinload(BeerCap.beer))

    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_beer_caps_by_beer_id(
    session: AsyncSession,
    beer_id: int,
    load_augmented_caps: bool = False,
    load_beer: bool = False,
) -> List[BeerCap]:
    stmt = select(BeerCap).where(BeerCap.beer_id == beer_id)

    if load_augmented_caps:
        stmt = stmt.options(selectinload(BeerCap.augmented_caps))
    if load_beer:
        stmt = stmt.options(selectinload(BeerCap.beer))

    result = await session.execute(stmt)
    return result.scalars().all()


async def get_all_beer_caps(
    session: AsyncSession,
    load_augmented_caps: bool = False,
    load_beer: bool = False,
) -> List[BeerCap]:
    stmt = select(BeerCap)

    if load_augmented_caps:
        stmt = stmt.options(selectinload(BeerCap.augmented_caps))
    if load_beer:
        stmt = stmt.options(selectinload(BeerCap.beer))

    result = await session.execute(stmt)
    return result.scalars().all()


async def delete_beer_cap(session: AsyncSession, beer_cap_id: int) -> None:
    cap = await get_beer_cap_by_id(session, beer_cap_id)
    if cap:
        await session.delete(cap)
        await session.commit()
