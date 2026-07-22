from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from .config import settings

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.SQL_ECHO,
    future=True,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


async def get_async_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
