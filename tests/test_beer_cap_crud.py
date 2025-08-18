from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.beer_cap.beer_cap_create import BeerCapCreateSchema
from src.api.schemas.beer_cap.beer_cap_update import BeerCapUpdateSchema
from src.api.schemas.country.country_create import CountryCreateSchema
from src.db.crud.beer_brand_crud import create_beer_brand
from src.db.crud.beer_cap_crud import (
    create_beer_cap,
    delete_beer_cap,
    get_all_beer_caps,
    get_beer_cap_by_id,
    get_beer_caps_by_beer_id,
    update_beer_cap,
)
from src.db.crud.beer_crud import create_beer
from src.db.crud.country_crud import create_country
from src.db.entities.beer_cap_entity import BeerCap


@pytest.mark.asyncio
class TestBeerCapCRUD:

    @pytest.fixture(autouse=True)
    async def _setup_beer(self, db_session: AsyncSession):
        beer_brand = await create_beer_brand(db_session, "Test Brand")
        country = await create_country(
            db_session, CountryCreateSchema(name="TestCountry")
        )
        self.beer = await create_beer(
            db_session,
            "Test Beer For Caps",
            beer_brand.id,
            rating=5,
            country_id=country.id,
        )
        assert self.beer.id is not None
        yield

    async def test_create_beer_cap(self, db_session: AsyncSession):
        today = date.today()
        cap = await create_beer_cap(
            db_session,
            self.beer.id,
            "test_cap_s3_key.jpg",
            BeerCapCreateSchema(filename="test_cap_s3_key.jpg", collected_date=today),
        )
        assert isinstance(cap, BeerCap)
        assert cap.id is not None
        assert cap.beer_id == self.beer.id
        assert cap.s3_key == "test_cap_s3_key.jpg"
        assert cap.collected_date == today

    async def test_get_beer_cap_by_id(self, db_session: AsyncSession):
        created_cap = await create_beer_cap(
            db_session,
            self.beer.id,
            "fetched_cap_s3_key.jpg",
            BeerCapCreateSchema(
                filename="fetched_cap_s3_key.jpg", collected_date=date.today()
            ),
        )
        fetched_cap = await get_beer_cap_by_id(db_session, created_cap.id)
        assert fetched_cap is not None
        assert fetched_cap.id == created_cap.id
        assert fetched_cap.s3_key == "fetched_cap_s3_key.jpg"

    async def test_get_beer_caps_by_beer_id(self, db_session: AsyncSession):
        beer_id = self.beer.id
        await create_beer_cap(
            db_session,
            beer_id,
            "cap_for_beer_1.jpg",
            BeerCapCreateSchema(
                filename="cap_for_beer_1.jpg", collected_date=date.today()
            ),
        )
        await create_beer_cap(
            db_session,
            beer_id,
            "cap_for_beer_2.jpg",
            BeerCapCreateSchema(
                filename="cap_for_beer_2.jpg", collected_date=date.today()
            ),
        )
        caps = await get_beer_caps_by_beer_id(db_session, beer_id)
        assert len(caps) == 2
        s3_keys = [c.s3_key for c in caps]
        assert "cap_for_beer_1.jpg" in s3_keys
        assert "cap_for_beer_2.jpg" in s3_keys

    async def test_update_beer_cap(self, db_session: AsyncSession):
        today = date.today()
        created_cap = await create_beer_cap(
            db_session,
            self.beer.id,
            "cap_to_update.jpg",
            BeerCapCreateSchema(filename="cap_to_update.jpg", collected_date=today),
        )

        new_date = date(2023, 1, 1)
        update_data = BeerCapUpdateSchema(
            variant_name="New Variant", collected_date=new_date
        )
        updated_cap = await update_beer_cap(db_session, created_cap.id, update_data)

        assert updated_cap is not None
        assert updated_cap.variant_name == "New Variant"
        assert updated_cap.collected_date == new_date

    async def test_get_all_beer_caps(self, db_session: AsyncSession):
        await create_beer_cap(
            db_session,
            self.beer.id,
            "cap_one.jpg",
            BeerCapCreateSchema(filename="cap_one.jpg", collected_date=date.today()),
        )
        await create_beer_cap(
            db_session,
            self.beer.id,
            "cap_two.jpg",
            BeerCapCreateSchema(filename="cap_two.jpg", collected_date=date.today()),
        )
        all_caps = await get_all_beer_caps(db_session)
        assert len(all_caps) == 2
        s3_keys = [c.s3_key for c in all_caps]
        assert "cap_one.jpg" in s3_keys
        assert "cap_two.jpg" in s3_keys

    async def test_delete_beer_cap(self, db_session: AsyncSession):
        new_cap = await create_beer_cap(
            db_session,
            self.beer.id,
            "delete_test_cap.jpg",
            BeerCapCreateSchema(
                filename="delete_test_cap.jpg", collected_date=date.today()
            ),
        )
        deleted = await delete_beer_cap(db_session, new_cap.id)
        assert deleted is True
        deleted_cap = await get_beer_cap_by_id(db_session, new_cap.id)
        assert deleted_cap is None
