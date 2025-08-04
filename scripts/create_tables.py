import asyncio

from src.db.utils import initialize_database

if __name__ == "__main__":
    asyncio.run(initialize_database())
