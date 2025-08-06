import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.country.country_create import CountryCreateSchema
from src.db.crud.beer_brand_crud import create_beer_brand
from src.db.crud.beer_cap_crud import create_beer_cap, delete_beer_cap, get_all_beer_caps, get_beer_cap_by_id
from src.db.crud.beer_crud import create_beer
from src.db.crud.country_crud import create_country
from src.db.entities.beer_cap_entity import BeerCap


@pytest.mark.asyncio
class TestBeerCapCRUD:

    @pytest.fixture(autouse=True)
    async def _setup_beer(self, db_session: AsyncSession):
        beer_brand = await create_beer_brand(db_session, "Test Brand")
        country = await create_country(db_session, CountryCreateSchema(name="TestCountry"))
        self.beer = await create_beer(db_session, "Test Beer For Caps", beer_brand.id, country_id=country.id)
        assert self.beer.id is not None
        yield

    async def test_create_beer_cap(self, db_session: AsyncSession):
        cap = await create_beer_cap(db_session, self.beer.id, "test_cap_s3_key.jpg")
        assert isinstance(cap, BeerCap)
        assert cap.id is not None
        assert cap.beer_id == self.beer.id
        assert cap.s3_key == "test_cap_s3_key.jpg"

    async def test_get_beer_cap_by_id(self, db_session: AsyncSession):
        created_cap = await create_beer_cap(db_session, self.beer.id, "fetched_cap_s3_key.jpg")
        fetched_cap = await get_beer_cap_by_id(db_session, created_cap.id)
        assert fetched_cap is not None
        assert fetched_cap.id == created_cap.id
        assert fetched_cap.s3_key == "fetched_cap_s3_key.jpg"

    async def test_get_all_beer_caps(self, db_session: AsyncSession):
        await create_beer_cap(db_session, self.beer.id, "cap_one.jpg")
        await create_beer_cap(db_session, self.beer.id, "cap_two.jpg")
        all_caps = await get_all_beer_caps(db_session)
        assert len(all_caps) == 2
        s3_keys = [c.s3_key for c in all_caps]
        assert "cap_one.jpg" in s3_keys
        assert "cap_two.jpg" in s3_keys

    async def test_delete_beer_cap(self, db_session: AsyncSession):
        new_cap = await create_beer_cap(db_session, self.beer.id, "delete_test_cap.jpg")
        await delete_beer_cap(db_session, new_cap.id)
        deleted_cap = await get_beer_cap_by_id(db_session, new_cap.id)
        assert deleted_cap is None
