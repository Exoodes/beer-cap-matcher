"""Merging duplicate beers, brands and countries into one.

Each merge moves everything that points at the source to the target and
then deletes the source, in one transaction. Afterwards the session is
expired, so the target is read back with its new beers or caps.
"""

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.crud.beer_brand_crud import get_beer_brand_by_id
from src.db.crud.beer_crud import get_beer_by_brand_and_name, get_beer_by_id
from src.db.crud.country_crud import get_country_by_id
from src.db.entities.beer_brand_entity import BeerBrand
from src.db.entities.beer_cap_entity import BeerCap
from src.db.entities.beer_entity import Beer
from src.db.entities.country_entity import Country


async def merge_beers(
    session: AsyncSession, source_id: int, target_id: int, commit: bool = True
) -> bool:
    """Moves the source beer's caps to the target and deletes the source.

    A country or rating the target lacks is taken from the source.

    Returns:
        False if either beer doesn't exist.
    """
    source = await get_beer_by_id(session, source_id)
    target = await get_beer_by_id(session, target_id)
    if not source or not target:
        return False

    await session.execute(
        update(BeerCap).where(BeerCap.beer_id == source.id).values(beer_id=target.id)
    )
    if target.country_id is None:
        target.country_id = source.country_id
    if not target.rating:
        target.rating = source.rating

    # Deleted with SQL: deleting the ORM object would lazy-load its caps.
    session.expunge(source)
    await session.execute(delete(Beer).where(Beer.id == source_id))

    if commit:
        await session.commit()
        session.expire_all()
    else:
        await session.flush()
    return True


async def merge_beer_brands(
    session: AsyncSession, source_id: int, target_id: int
) -> bool:
    """Moves the source brand's beers to the target and deletes the source.

    A beer whose name the target brand already has is merged into that beer,
    so its caps end up in one place.

    Returns:
        False if either brand doesn't exist.
    """
    source = await get_beer_brand_by_id(session, source_id)
    target = await get_beer_brand_by_id(session, target_id)
    if not source or not target:
        return False

    result = await session.execute(select(Beer).where(Beer.beer_brand_id == source_id))
    for beer in list(result.scalars().all()):
        twin = await get_beer_by_brand_and_name(session, target_id, beer.name)
        if twin:
            await merge_beers(session, beer.id, twin.id, commit=False)
        else:
            beer.beer_brand_id = target_id
    await session.flush()

    session.expunge(source)
    await session.execute(delete(BeerBrand).where(BeerBrand.id == source_id))
    await session.commit()
    session.expire_all()
    return True


async def merge_countries(
    session: AsyncSession, source_id: int, target_id: int
) -> bool:
    """Moves the source country's beers to the target and deletes the source.

    Returns:
        False if either country doesn't exist.
    """
    source = await get_country_by_id(session, source_id)
    target = await get_country_by_id(session, target_id)
    if not source or not target:
        return False

    await session.execute(
        update(Beer).where(Beer.country_id == source_id).values(country_id=target_id)
    )
    session.expunge(source)
    await session.execute(delete(Country).where(Country.id == source_id))
    await session.commit()
    session.expire_all()
    return True
