from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.beer import Beer


async def create_beer(session: AsyncSession, name: str) -> Beer:
    beer = Beer(name=name)
    session.add(beer)
    await session.commit()
    await session.refresh(beer)
    return beer


async def get_beer_by_id(session: AsyncSession, beer_id: int) -> Optional[Beer]:
    result = await session.execute(select(Beer).where(Beer.id == beer_id))
    return result.scalar_one_or_none()


async def get_beer_by_name(session: AsyncSession, name: str) -> Optional[Beer]:
    result = await session.execute(select(Beer).where(Beer.name == name))
    return result.scalar_one_or_none()


async def get_all_beers(session: AsyncSession) -> List[Beer]:
    result = await session.execute(select(Beer))
    return result.scalars().all()


async def delete_beer(session: AsyncSession, beer_id: int) -> None:
    beer = await get_beer_by_id(session, beer_id)

    if beer:
        await session.delete(beer)
        await session.commit()
