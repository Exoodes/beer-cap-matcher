import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.crud_beer import create_beer, delete_beer, get_all_beers, get_beer_by_id
from src.models.beer import Beer


@pytest.mark.asyncio
class TestBeerCRUD:

    async def test_create_beer(self, db_session: AsyncSession):
        beer = await create_beer(db_session, "Test Beer")
        assert isinstance(beer, Beer)
        assert beer.id is not None
        assert beer.name == "Test Beer"

    async def test_get_beer_by_id(self, db_session: AsyncSession):
        created_beer = await create_beer(db_session, "ID Test Beer")
        fetched_beer = await get_beer_by_id(db_session, created_beer.id)
        assert fetched_beer is not None
        assert fetched_beer.id == created_beer.id
        assert fetched_beer.name == "ID Test Beer"

    async def test_get_all_beers(self, db_session: AsyncSession):
        await create_beer(db_session, "Beer One")
        await create_beer(db_session, "Beer Two")
        beers = await get_all_beers(db_session)
        assert len(beers) == 2
        names = [beer.name for beer in beers]
        assert "Beer One" in names
        assert "Beer Two" in names

    async def test_delete_beer(self, db_session: AsyncSession):
        created_beer = await create_beer(db_session, "Delete Test Beer")
        beer_id = created_beer.id
        await delete_beer(db_session, beer_id)
        deleted_beer = await get_beer_by_id(db_session, beer_id)
        assert deleted_beer is None

    async def test_delete_non_existent_beer_does_nothing(self, db_session: AsyncSession):
        initial_beers = await get_all_beers(db_session)
        await delete_beer(db_session, 99999)
        final_beers = await get_all_beers(db_session)
        assert len(initial_beers) == len(final_beers)
