import asyncio
import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

from src.api.schemas.beer_cap.beer_cap_create import BeerCapCreateSchema
from src.api.schemas.country.country_create import CountryCreateSchema
from src.db.beer_caps_seed import data as BEER_CAPS_DATA
from src.db.crud.beer_brand_crud import create_beer_brand
from src.db.crud.beer_crud import create_beer
from src.db.crud.country_crud import create_country
from src.db.database import GLOBAL_ASYNC_SESSION_MAKER
from src.services.beer_cap_facade import BeerCapFacade
from src.storage.minio.minio_client import MinioClientWrapper

IMAGE_DIR = Path("data/images")


async def seed_beer_caps(data: Dict[str, Dict[str, Dict[str, list[Dict[str, Any]]]]]) -> None:
    """Seed database and MinIO with initial beer cap data."""
    load_dotenv()
    minio_wrapper = MinioClientWrapper()
    facade = BeerCapFacade(minio_wrapper)

    minio_wrapper.ensure_buckets_exist([facade.original_caps_bucket, facade.augmented_caps_bucket])

    async with GLOBAL_ASYNC_SESSION_MAKER() as session:
        for country_name, brands in data.items():
            country = await create_country(session, CountryCreateSchema(name=country_name))

            for brand_name, beers in brands.items():
                beer_brand = await create_beer_brand(session, brand_name)

                for beer_name, caps in beers.items():
                    beer = await create_beer(session, beer_name, beer_brand.id, country_id=country.id)

                    for cap in caps:
                        filename = cap["file_name"]
                        variant = cap.get("variant")
                        cap_schema = BeerCapCreateSchema(filename=filename, variant_name=variant)
                        image_path = IMAGE_DIR / filename

                        with open(image_path, "rb") as image_file:
                            length = os.path.getsize(image_path)
                            await facade.create_cap_for_existing_beer_and_upload(
                                beer.id, cap_schema, image_file, length, content_type="image/jpeg"
                            )


if __name__ == "__main__":
    asyncio.run(seed_beer_caps(BEER_CAPS_DATA))
