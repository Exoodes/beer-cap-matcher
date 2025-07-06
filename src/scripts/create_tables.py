import asyncio

import src.db.entities.augmented_cap as _
import src.db.entities.beer as _
import src.db.entities.beer_cap as _
from src.db.database import engine
from src.db.entities import Base


async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(init_models())
