import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.beer_brand.beer_brand_update import BeerBrandUpdateSchema
from src.db.crud.beer_brand_crud import (
    create_beer_brand,
    delete_beer_brand,
    get_all_beer_brands,
    get_beer_brand_by_id,
    get_beer_brand_by_name,
    update_beer_brand,
)
from src.db.entities.beer_brand_entity import BeerBrand


@pytest.mark.asyncio
class TestBeerBrandCRUD:
    async def test_create_beer_brand(self, db_session: AsyncSession):
        beer_brand = await create_beer_brand(db_session, "Test Beer Brand")
        assert isinstance(beer_brand, BeerBrand)
        assert beer_brand.id is not None
        assert beer_brand.name == "Test Beer Brand"

    async def test_get_beer_brand_by_id(self, db_session: AsyncSession):
        created = await create_beer_brand(db_session, "Lookup Beer Brand")
        fetched = await get_beer_brand_by_id(db_session, created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.name == "Lookup Beer Brand"

    async def test_get_beer_brand_by_name(self, db_session: AsyncSession):
        await create_beer_brand(db_session, "Name Lookup Brand")
        fetched = await get_beer_brand_by_name(db_session, "Name Lookup Brand")
        assert fetched is not None
        assert fetched.name == "Name Lookup Brand"

    async def test_get_all_beer_brands(self, db_session: AsyncSession):
        await create_beer_brand(db_session, "Beer Brand One")
        await create_beer_brand(db_session, "Beer Brand Two")
        beer_brands = await get_all_beer_brands(db_session)
        assert len(beer_brands) == 2
        names = [b.name for b in beer_brands]
        assert "Beer Brand One" in names
        assert "Beer Brand Two" in names

    async def test_update_beer_brand(self, db_session: AsyncSession):
        created_brand = await create_beer_brand(db_session, "Brand to Update")
        update_data = BeerBrandUpdateSchema(name="Updated Brand Name")
        updated_brand = await update_beer_brand(
            db_session, created_brand.id, update_data
        )
        assert updated_brand.name == "Updated Brand Name"

    async def test_delete_beer_brand(self, db_session: AsyncSession):
        beer_brand = await create_beer_brand(db_session, "Delete Beer Brand")
        deleted = await delete_beer_brand(db_session, beer_brand.id)
        assert deleted is True
        deleted_brand = await get_beer_brand_by_id(db_session, beer_brand.id)
        assert deleted_brand is None
