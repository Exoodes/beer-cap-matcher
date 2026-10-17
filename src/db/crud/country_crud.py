from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.schemas.country.country_create import CountryCreateSchema
from src.api.schemas.country.country_update import CountryUpdateSchema
from src.db.entities.beer_entity import Beer
from src.db.entities.country_entity import Country


async def create_country(
    session: AsyncSession, data: CountryCreateSchema, commit: bool = True
) -> Country:
    country = Country(name=data.name, description=data.description)
    session.add(country)

    if commit:
        await session.commit()
    else:
        await session.flush()

    await session.refresh(country)
    return country


async def get_country_by_id(
    session: AsyncSession,
    country_id: int,
    load_beers: bool = False,
) -> Optional[Country]:
    stmt = select(Country).where(Country.id == country_id)

    if load_beers:
        stmt = stmt.options(selectinload(Country.beers))

    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_country_by_name(session: AsyncSession, name: str) -> Optional[Country]:
    """Retrieves a country by its name, ignoring case."""
    stmt = select(Country).where(func.lower(Country.name) == func.lower(name))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_all_countries(
    session: AsyncSession,
    load_beers: bool = False,
) -> list[Country]:
    stmt = select(Country)

    if load_beers:
        stmt = stmt.options(selectinload(Country.beers))

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_beers_by_country(session: AsyncSession) -> dict[int, int]:
    """Number of beers from each country; countries without beers are left out."""
    result = await session.execute(
        select(Beer.country_id, func.count())
        .where(Beer.country_id.is_not(None))
        .group_by(Beer.country_id)
    )
    return {country_id: count for country_id, count in result.tuples() if country_id}


async def delete_country(session: AsyncSession, country_id: int) -> bool:
    country = await get_country_by_id(session, country_id)

    if country:
        await session.delete(country)
        await session.commit()

    return country is not None


async def update_country(
    session: AsyncSession,
    country_id: int,
    update_data: CountryUpdateSchema,
    load_beers: bool = False,
) -> Optional[Country]:
    stmt = select(Country).where(Country.id == country_id)

    if load_beers:
        stmt = stmt.options(selectinload(Country.beers))

    result = await session.execute(stmt)
    country = result.scalar_one_or_none()

    if not country:
        return None

    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(country, field, value)

    await session.commit()
    await session.refresh(country)
    return country
