"""Database engine, session factory and declarative base.

Shared by the whole application. Import `Base` into a model module so the table
is registered for migrations, and use `get_async_session` as a FastAPI
dependency rather than creating sessions by hand.
"""

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from .config import settings

# Pool sizing: up to 10 long-lived connections, 20 more under burst, then wait
# up to 30s. Connections are recycled every 30 minutes to stay valid behind
# proxies that time out idle sockets, and pre-pinged before reuse so a severed
# connection fails fast rather than surfacing as a query error.
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
# expire_on_commit=False keeps model attributes readable after commit, so code
# can use a freshly written object without an extra SELECT.
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


async def get_async_session() -> AsyncSession:
    """FastAPI dependency yielding a request-scoped session.

    The session is closed automatically when the request finishes. Nothing is
    committed here; each CRUD function owns its own commit.
    """
    async with AsyncSessionLocal() as session:
        yield session
