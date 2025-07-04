import os

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("POSTGRES_DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=False, future=True)

async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
