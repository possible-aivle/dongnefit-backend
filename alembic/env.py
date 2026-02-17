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
    AdministrativeEmd,
    AdministrativeSgg,
    AdministrativeSido,
    AncillaryLand,
    BlogPost,
    BuildingRegisterAncillaryLot,
    BuildingRegisterArea,
    BuildingRegisterFloorDetail,
    BuildingRegisterGeneral,
    BuildingRegisterHeader,
    Discussion,
    DiscussionLike,
    DiscussionReply,
    FileStorage,
    GisBuildingIntegrated,
    LandAndForestInfo,
    LandCharacteristic,
    LandOwnership,
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

# PostGIS tiger/topology 테이블을 autogenerate에서 제외
_EXCLUDE_TABLES = frozenset({
    "spatial_ref_sys",
    # tiger geocoder tables
    "addr", "addrfeat", "bg", "county", "county_lookup", "countysub_lookup",
    "cousub", "direction_lookup", "edges", "faces", "featnames",
    "geocode_settings", "geocode_settings_default", "loader_lookuptables",
    "loader_platform", "loader_variables", "pagc_gaz", "pagc_lex", "pagc_rules",
    "place", "place_lookup", "secondary_unit_lookup", "state", "state_lookup",
    "street_type_lookup", "tabblock", "tabblock20", "tract", "zcta5",
    "zip_lookup", "zip_lookup_all", "zip_lookup_base", "zip_state", "zip_state_loc",
    # topology tables
    "topology", "layer",
})


def include_name(name: str, type_: str, parent_names: dict) -> bool:
    """Autogenerate 대상 필터: tiger/topology 테이블 제외."""
    if type_ == "table":
        return name not in _EXCLUDE_TABLES
    return True


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
        include_name=include_name,
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
        include_name=include_name,
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
