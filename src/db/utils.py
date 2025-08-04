from dotenv import load_dotenv

from src.db.database import GLOBAL_ENGINE
from src.db.entities import Base

load_dotenv()


async def initialize_database() -> None:
    """Initializes the database by creating all necessary tables.

    This asynchronous function connects to the database using the global
    engine and creates all tables defined in the SQLAlchemy Base metadata.
    """
    async with GLOBAL_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
