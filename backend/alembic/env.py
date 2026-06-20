"""Alembic environment — reads DB URL from app.core.config, runs raw SQL migrations.

We use raw asyncpg at runtime (no SQLAlchemy ORM). Alembic uses SQLAlchemy
solely as a migration runner. Migrations contain raw SQL via op.execute().
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# Load app settings for the database URL
from app.core.config import settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Build asyncpg DSN for SQLAlchemy (postgresql+asyncpg://user:pass@host:port/db)
_RAW_DSN = settings.pg_dsn  # postgresql://user:pass@host:port/db
_ASYNC_DSN = _RAW_DSN.replace("postgresql://", "postgresql+asyncpg://")

target_metadata = None  # Raw SQL mode — no ORM models


def _get_url():
    return _ASYNC_DSN


def run_migrations_offline():
    url = _get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    connectable = create_async_engine(_get_url(), poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
