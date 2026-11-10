from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import declarative_base, sessionmaker

import config


def normalise_database_url(url: str) -> str:
    """Make every Postgres URL use the psycopg (version 3) driver from requirements.txt.

    Hosts hand out "postgres://..." (which SQLAlchemy doesn't recognise) or "postgresql://..." (which
    uses whichever driver your SQLAlchemy version defaults to). Both become "postgresql+psycopg://...".
    """
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


DATABASE_URL = normalise_database_url(config.DATABASE_URL)

# SQLite needs a special check; PostgreSQL does not
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}


# pool_pre_ping: test each pooled connection before using it and replace it if the database closed it.
# Neon's free plan suspends the database when idle, which silently closes every open connection.
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

ALEMBIC_INI = Path(__file__).resolve().parent / "alembic.ini"
# The first migration: exactly the tables Base.metadata.create_all used to make
BASELINE_REVISION = "0001_baseline"


def get_db():
    """Provides a database session to FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def upgrade_database() -> None:
    """Brings the database up to the latest migration (like Django's `manage.py migrate`).

    A database made by the old Base.metadata.create_all() has every table but no record of migrations.
    It already matches the baseline migration, so it is marked as being at that point first, rather
    than the baseline trying to create tables that already exist.
    """
    from alembic import command
    from alembic.config import Config

    config = Config(str(ALEMBIC_INI))
    tables = inspect(engine).get_table_names()
    if "users" in tables and "alembic_version" not in tables:
        command.stamp(config, BASELINE_REVISION)
    command.upgrade(config, "head")