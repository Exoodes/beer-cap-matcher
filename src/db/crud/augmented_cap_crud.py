from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.entities.augmented_cap_entity import AugmentedCap


async def create_augmented_cap(
    session: AsyncSession, beer_cap_id: int, s3_key: str
) -> AugmentedCap:
    new_aug = AugmentedCap(beer_cap_id=beer_cap_id, s3_key=s3_key)
    session.add(new_aug)
    await session.commit()
    await session.refresh(new_aug)
    return new_aug


async def get_augmented_cap_by_id(
    session: AsyncSession, augmented_cap_id: int
) -> Optional[AugmentedCap]:
    result = await session.execute(
        select(AugmentedCap).where(AugmentedCap.id == augmented_cap_id)
    )
    return result.scalar_one_or_none()


async def get_all_augmented_caps(session: AsyncSession) -> list[AugmentedCap]:
    result = await session.execute(select(AugmentedCap))
    return list(result.scalars().all())


async def delete_augmented_cap(session: AsyncSession, augmented_cap_id: int) -> bool:
    aug = await get_augmented_cap_by_id(session, augmented_cap_id)
    if aug:
        await session.delete(aug)
        await session.commit()
        return True
    return False
