import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine  # <-- Use Async Engine

from alembic import context

# 1. PATH FIX: Dynamically add the backend root folder to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 2. Load Environment Variables from .env
try:
    from dotenv import load_dotenv
    dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
    load_dotenv(dotenv_path)
except ImportError:
    pass

# 3. Direct Base Import
from app.database import Base

# 4. Import your models package to trigger registration of all tables
try:
    import app.models
except Exception as e:
    raise e

target_metadata = Base.metadata

# This is the Alembic Config object
config = context.config

# 5. DYNAMIC DATABASE URL INJECTION (with Async Driver Fallback)
database_url = os.getenv("DATABASE_URL")
if database_url:
    # Ensure correct dialect prefix (SQLAlchemy requires postgresql+asyncpg:// for async tasks)
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgresql://") and "+asyncpg" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
    config.set_main_option("sqlalchemy.url", database_url)
else:
    raise ValueError("DATABASE_URL not found in environment variables or .env file.")

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    """Helper to run migrations in a synchronous context."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode using an AsyncEngine."""
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        # Alembic migrations are sync, so we run them inside a sync wrapper 
        # using the async connection
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    # Run the online migrations using an asyncio event loop
    asyncio.run(run_migrations_online())