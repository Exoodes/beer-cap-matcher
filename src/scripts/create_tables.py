import asyncio

import src.models.augmented_cap as _
import src.models.beer as _
import src.models.beer_cap as _
from src.database import engine
from src.models import Base


async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(init_models())
