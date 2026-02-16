"""Alembic migration environment configuration."""

import asyncio
from logging.config import fileConfig

from geoalchemy2 import alembic_helpers
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlmodel import SQLModel

from alembic import context
from app.config import settings
from app.models import (  # noqa: F401 - Import all models for autogenerate
    AdministrativeDivision,
    AdministrativeEmd,
    AncillaryLand,
    BlogPost,
    BuildingRegisterFloorDetail,
    BuildingRegisterHeader,
    Discussion,
    DiscussionLike,
    DiscussionReply,
    FileStorage,
    LandAndForestInfo,
    LandCharacteristic,
    LandUsePlan,
    Lot,
    Neighborhood,
    Notification,
    NotificationSettings,
    OfficialLandPrice,
    RealEstateRental,
    RealEstateSale,
    Report,
    ReportCategory,
    ReportReview,
    RoadCenterLine,
    User,
    UseRegionDistrict,
)

# Alembic Config object
config = context.config

# Set database URL from settings (keep asyncpg for async migrations)
config.set_main_option("sqlalchemy.url", settings.database_url)

# Setup loggers
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model metadata for autogenerate
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        process_revision_directives=alembic_helpers.writer,
        render_item=alembic_helpers.render_item,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        process_revision_directives=alembic_helpers.writer,
        render_item=alembic_helpers.render_item,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in async mode."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
