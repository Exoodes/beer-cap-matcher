import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.country.country_create import CountryCreateSchema
from src.db.crud.augmented_cap_crud import (
    create_augmented_cap,
    delete_augmented_cap,
    get_all_augmented_caps,
    get_augmented_cap_by_id,
)
from src.db.crud.beer_brand_crud import create_beer_brand
from src.db.crud.beer_cap_crud import create_beer_cap
from src.db.crud.beer_crud import create_beer
from src.db.crud.country_crud import create_country
from src.db.entities.augmented_cap_entity import AugmentedCap


@pytest.mark.asyncio
class TestAugmentedCapCRUD:

    @pytest.fixture(autouse=True)
    async def _setup_beer_and_cap(self, db_session: AsyncSession):
        beer_brand = await create_beer_brand(db_session, "Test Brand")
        country = await create_country(db_session, CountryCreateSchema(name="AugCountry"))
        self.beer = await create_beer(db_session, "Test Beer For Augmented Caps", rating=6, beer_brand.id, country_id=country.id)
        self.beer_cap = await create_beer_cap(db_session, self.beer.id, "base_cap_for_aug_tests.jpg")
        assert self.beer_cap.id is not None
        yield

    async def test_create_augmented_cap(self, db_session: AsyncSession):
        aug = await create_augmented_cap(db_session, self.beer_cap.id, "test_s3_key.jpg")
        assert isinstance(aug, AugmentedCap)
        assert aug.id is not None
        assert aug.beer_cap_id == self.beer_cap.id
        assert aug.s3_key == "test_s3_key.jpg"

    async def test_get_augmented_cap_by_id(self, db_session: AsyncSession):
        created_aug = await create_augmented_cap(db_session, self.beer_cap.id, "fetched_aug_s3_key.jpg")
        fetched_aug = await get_augmented_cap_by_id(db_session, created_aug.id)
        assert fetched_aug is not None
        assert fetched_aug.id == created_aug.id
        assert fetched_aug.s3_key == "fetched_aug_s3_key.jpg"

    async def test_get_all_augmented_caps(self, db_session: AsyncSession):
        await create_augmented_cap(db_session, self.beer_cap.id, "aug_one.jpg")
        await create_augmented_cap(db_session, self.beer_cap.id, "aug_two.jpg")
        all_augs = await get_all_augmented_caps(db_session)
        assert len(all_augs) == 2
        s3_keys = [a.s3_key for a in all_augs]
        assert "aug_one.jpg" in s3_keys
        assert "aug_two.jpg" in s3_keys

    async def test_delete_augmented_cap(self, db_session: AsyncSession):
        aug = await create_augmented_cap(db_session, self.beer_cap.id, "delete_aug_s3_key.jpg")
        await delete_augmented_cap(db_session, aug.id)
        deleted_aug = await get_augmented_cap_by_id(db_session, aug.id)
        assert deleted_aug is None
