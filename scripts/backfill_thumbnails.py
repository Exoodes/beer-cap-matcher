"""Creates thumbnails for caps that don't have one yet.

The API also does this in the background on startup; this script is for
running it by hand.
"""

import asyncio

from src.services.beer_cap_facade import BeerCapFacade
from src.storage.minio.minio_client import MinioClientWrapper


async def main() -> None:
    created = await BeerCapFacade(MinioClientWrapper()).backfill_thumbnails()
    print(f"Created {created} thumbnails.")


if __name__ == "__main__":
    asyncio.run(main())
