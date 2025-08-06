import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.beer.beer_update import BeerUpdateSchema
from src.api.schemas.country.country_create import CountryCreateSchema
from src.db.crud.beer_brand_crud import create_beer_brand
from src.db.crud.beer_crud import create_beer, delete_beer, get_all_beers, get_beer_by_id, update_beer
from src.db.crud.country_crud import create_country
from src.db.entities.beer_entity import Beer


@pytest.mark.asyncio
class TestBeerCRUD:
    @pytest.fixture(autouse=True)
    async def _setup_beer_brand(self, db_session: AsyncSession):
        self.beer_brand = await create_beer_brand(db_session, "Test Beer Brand")
        yield

    async def test_create_beer(self, db_session: AsyncSession):
        country = await create_country(db_session, CountryCreateSchema(name="USA"))
        beer = await create_beer(
            db_session, "Test Beer", rating=7, country_id=country.id, beer_brand_id=self.beer_brand.id
        )
        assert isinstance(beer, Beer)
        assert beer.id is not None
        assert beer.name == "Test Beer"
        assert beer.rating == 7
        assert beer.country_id == country.id

    async def test_get_beer_by_id(self, db_session: AsyncSession):
        country = await create_country(db_session, CountryCreateSchema(name="Germany"))
        created_beer = await create_beer(
            db_session, "ID Test Beer", rating=4, country_id=country.id, beer_brand_id=self.beer_brand.id
        )
        fetched_beer = await get_beer_by_id(db_session, created_beer.id, load_country=True)
        assert fetched_beer is not None
        assert fetched_beer.id == created_beer.id
        assert fetched_beer.name == "ID Test Beer"
        assert fetched_beer.rating == 4
        assert fetched_beer.country_id == country.id

    async def test_get_all_beers(self, db_session: AsyncSession):
        country = await create_country(db_session, CountryCreateSchema(name="UK"))
        await create_beer(db_session, "Beer One", rating=1, country_id=country.id, beer_brand_id=self.beer_brand.id)
        await create_beer(db_session, "Beer Two", rating=2, country_id=country.id, beer_brand_id=self.beer_brand.id)
        beers = await get_all_beers(db_session, load_country=True)
        assert len(beers) == 2
        names = [beer.name for beer in beers]
        ratings = [beer.rating for beer in beers]
        assert "Beer One" in names
        assert "Beer Two" in names
        assert 1 in ratings and 2 in ratings
        assert all(beer.country_id == country.id for beer in beers)

    async def test_delete_beer(self, db_session: AsyncSession):
        country = await create_country(db_session, CountryCreateSchema(name="Belgium"))
        created_beer = await create_beer(
            db_session, "Delete Test Beer", rating=3, country_id=country.id, beer_brand_id=self.beer_brand.id
        )
        beer_id = created_beer.id
        await delete_beer(db_session, beer_id)
        deleted_beer = await get_beer_by_id(db_session, beer_id)
        assert deleted_beer is None

    async def test_update_beer_rating(self, db_session: AsyncSession):
        beer = await create_beer(db_session, "Rate Me", rating=2)
        updated = await update_beer(db_session, beer.id, BeerUpdateSchema(rating=9))
        assert updated is not None
        assert updated.rating == 9

    async def test_delete_non_existent_beer_does_nothing(self, db_session: AsyncSession):
        initial_beers = await get_all_beers(db_session)
        await delete_beer(db_session, 99999)
        final_beers = await get_all_beers(db_session)
        assert len(initial_beers) == len(final_beers)
