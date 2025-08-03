import asyncio

from dotenv import load_dotenv

import src.db.entities.augmented_cap_entity as _
import src.db.entities.beer_cap_entity as _
import src.db.entities.beer_entity as _
from src.db.database import GLOBAL_ENGINE
from src.db.entities import Base

load_dotenv()


async def init_models():
    async with GLOBAL_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(init_models())
