from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.schemas.beer_cap.update_schema import BeerCapUpdateSchema
from src.db.entities.beer_cap import BeerCap
from src.schemas.beer_cap_schema import BeerCapCreateSchema


async def create_beer_cap(
    session: AsyncSession, beer_id: int, s3_key: str, data: BeerCapCreateSchema, commit: bool = True
) -> BeerCap:
    new_cap = BeerCap(beer_id=beer_id, s3_key=s3_key, variant_name=data.variant_name)
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


async def delete_beer_cap(session: AsyncSession, beer_cap_id: int) -> bool:
    cap = await get_beer_cap_by_id(session, beer_cap_id)
    if cap:
        await session.delete(cap)
        await session.commit()

    return cap is not None


async def update_beer_cap(
    session: AsyncSession,
    beer_cap_id: int,
    update_data: BeerCapUpdateSchema,
    load_beer: bool = False,
    load_augmented_caps: bool = False,
) -> Optional[BeerCap]:
    stmt = select(BeerCap).where(BeerCap.id == beer_cap_id)

    if load_beer:
        stmt = stmt.options(selectinload(BeerCap.beer))
    if load_augmented_caps:
        stmt = stmt.options(selectinload(BeerCap.augmented_caps))

    result = await session.execute(stmt)
    beer_cap = result.scalar_one_or_none()

    if not beer_cap:
        return None

    if update_data.variant_name is not None:
        beer_cap.variant_name = update_data.variant_name

    await session.commit()
    await session.refresh(beer_cap)
    return beer_cap
