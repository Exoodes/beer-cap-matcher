from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.entities.beer import Beer


async def create_beer(session: AsyncSession, name: str, commit: bool = True) -> Beer:
    beer = Beer(name=name)
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
) -> Optional[Beer]:
    stmt = select(Beer).where(Beer.id == beer_id)

    if load_caps:
        stmt = stmt.options(selectinload(Beer.caps))

    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_all_beers(
    session: AsyncSession,
    load_caps: bool = False,
) -> List[Beer]:
    stmt = select(Beer)

    if load_caps:
        stmt = stmt.options(selectinload(Beer.caps))

    result = await session.execute(stmt)
    return result.scalars().all()


async def delete_beer(session: AsyncSession, beer_id: int) -> bool:
    beer = await get_beer_by_id(session, beer_id)

    if beer:
        await session.delete(beer)
        await session.commit()

    return beer is not None
