from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

DATABASE_URL = (
    f"postgresql+asyncpg://"
    f"{settings.ORDERS_DB_USER}:"
    f"{settings.ORDERS_DB_PASSWORD}"
    f"@{settings.ORDERS_DB_HOST}:"
    f"{settings.ORDERS_DB_PORT}/"
    f"{settings.ORDERS_DB_NAME}"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    future=True
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async_session = AsyncSessionLocal()
    try:
        yield async_session
    finally:
        await async_session.close()
