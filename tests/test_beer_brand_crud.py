import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.crud.beer_brand_crud import create_beer_brand, delete_beer_brand, get_all_beer_brands, get_beer_brand_by_id
from src.db.entities.beer_brand_entity import BeerBrand


@pytest.mark.asyncio
class TestBeerBrandCRUD:
    async def test_create_beer_brand(self, db_session: AsyncSession):
        beer_brand = await create_beer_brand(db_session, "Test Beer Brand", "A test beer brand")
        assert isinstance(beer_brand, BeerBrand)
        assert beer_brand.id is not None
        assert beer_brand.name == "Test Beer Brand"

    async def test_get_beer_brand_by_id(self, db_session: AsyncSession):
        created = await create_beer_brand(db_session, "Lookup Beer Brand", "A test beer brand")
        fetched = await get_beer_brand_by_id(db_session, created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.name == "Lookup Beer Brand"

    async def test_get_all_beer_brands(self, db_session: AsyncSession):
        await create_beer_brand(db_session, "Beer Brand One", "A test beer brand")
        await create_beer_brand(db_session, "Beer Brand Two", "A test beer brand")
        beer_brands = await get_all_beer_brands(db_session)
        assert len(beer_brands) == 2
        names = [b.name for b in beer_brands]
        assert "Beer Brand One" in names
        assert "Beer Brand Two" in names

    async def test_delete_beer_brand(self, db_session: AsyncSession):
        beer_brand = await create_beer_brand(db_session, "Delete Beer Brand", "A test beer brand")
        await delete_beer_brand(db_session, beer_brand.id)
        deleted = await get_beer_brand_by_id(db_session, beer_brand.id)
        assert deleted is None
