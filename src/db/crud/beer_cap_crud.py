from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.schemas.beer_cap.beer_cap_create import BeerCapCreateSchema
from src.api.schemas.beer_cap.beer_cap_update import BeerCapUpdateSchema
from src.db.entities.beer_cap_entity import BeerCap
from src.db.entities.beer_entity import Beer


async def create_beer_cap(
    session: AsyncSession,
    beer_id: int,
    s3_key: str,
    data: BeerCapCreateSchema,
    commit: bool = True,
) -> BeerCap:
    new_cap = BeerCap(
        beer_id=beer_id,
        s3_key=s3_key,
        variant_name=data.variant_name,
        collected_date=data.collected_date,
    )
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
        stmt = stmt.options(
            selectinload(BeerCap.beer).selectinload(Beer.beer_brand),
            selectinload(BeerCap.beer).selectinload(Beer.country),
        )

    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_beer_caps_by_beer_id(
    session: AsyncSession,
    beer_id: int,
    load_augmented_caps: bool = False,
    load_beer: bool = False,
) -> list[BeerCap]:
    stmt = select(BeerCap).where(BeerCap.beer_id == beer_id)

    if load_augmented_caps:
        stmt = stmt.options(selectinload(BeerCap.augmented_caps))
    if load_beer:
        stmt = stmt.options(selectinload(BeerCap.beer))

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_all_beer_caps(
    session: AsyncSession,
    load_augmented_caps: bool = False,
    load_beer: bool = False,
) -> list[BeerCap]:
    stmt = select(BeerCap)

    if load_augmented_caps:
        stmt = stmt.options(selectinload(BeerCap.augmented_caps))
    if load_beer:
        stmt = stmt.options(
            selectinload(BeerCap.beer).selectinload(Beer.beer_brand),
            selectinload(BeerCap.beer).selectinload(Beer.country),
        )

    result = await session.execute(stmt)
    return list(result.scalars().all())


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
        stmt = stmt.options(
            selectinload(BeerCap.beer).selectinload(Beer.beer_brand),
            selectinload(BeerCap.beer).selectinload(Beer.country),
        )
    if load_augmented_caps:
        stmt = stmt.options(selectinload(BeerCap.augmented_caps))

    result = await session.execute(stmt)
    beer_cap = result.scalar_one_or_none()

    if not beer_cap:
        return None

    if update_data.variant_name is not None:
        beer_cap.variant_name = update_data.variant_name

    if update_data.beer_id is not None:
        beer_cap.beer_id = update_data.beer_id

    if update_data.collected_date is not None:
        setattr(beer_cap, "collected_date", update_data.collected_date)

    await session.commit()
    await session.refresh(beer_cap)
    return beer_cap
