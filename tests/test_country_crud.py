import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.country.country_create import CountryCreateSchema
from src.api.schemas.country.country_update import CountryUpdateSchema
from src.db.crud.country_crud import (
    create_country,
    delete_country,
    get_all_countries,
    get_country_by_id,
    update_country,
)
from src.db.entities.country_entity import Country


@pytest.mark.asyncio
class TestCountryCRUD:
    async def test_create_country(self, db_session: AsyncSession):
        data = CountryCreateSchema(name="Testland", description="Desc")
        country = await create_country(db_session, data)
        assert isinstance(country, Country)
        assert country.id is not None
        assert country.name == "Testland"

    async def test_get_country_by_id(self, db_session: AsyncSession):
        created = await create_country(db_session, CountryCreateSchema(name="IDLand"))
        fetched = await get_country_by_id(db_session, created.id)
        assert fetched is not None
        assert fetched.id == created.id

    async def test_get_all_countries(self, db_session: AsyncSession):
        await create_country(db_session, CountryCreateSchema(name="CountryA"))
        await create_country(db_session, CountryCreateSchema(name="CountryB"))
        countries = await get_all_countries(db_session)
        assert len(countries) == 2
        names = {c.name for c in countries}
        assert {"CountryA", "CountryB"} == names

    async def test_update_country(self, db_session: AsyncSession):
        created = await create_country(db_session, CountryCreateSchema(name="Old"))
        updated = await update_country(
            db_session, created.id, CountryUpdateSchema(name="New")
        )
        assert updated is not None
        assert updated.name == "New"

    async def test_delete_country(self, db_session: AsyncSession):
        created = await create_country(db_session, CountryCreateSchema(name="DeleteMe"))
        await delete_country(db_session, created.id)
        assert await get_country_by_id(db_session, created.id) is None
