"""Connecting to the database: SQLite locally, Postgres (Neon) when deployed."""
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from database import engine, normalise_database_url

# ---------- Database URLs from hosting providers ----------

def test_postgres_scheme_uses_psycopg():
    assert normalise_database_url("postgres://u:p@host/db") == "postgresql+psycopg://u:p@host/db"


def test_postgresql_scheme_uses_psycopg():
    assert normalise_database_url("postgresql://u:p@host/db") == "postgresql+psycopg://u:p@host/db"


def test_url_already_naming_psycopg_is_unchanged():
    assert normalise_database_url("postgresql+psycopg://u:p@host/db") == "postgresql+psycopg://u:p@host/db"


def test_neon_connection_options_are_kept():
    url = "postgresql://u:p@ep-x.eu-west-2.aws.neon.tech/db?sslmode=require&channel_binding=require"
    assert normalise_database_url(url).endswith("/db?sslmode=require&channel_binding=require")


def test_sqlite_url_is_unchanged():
    assert normalise_database_url("sqlite:///./test.db") == "sqlite:///./test.db"


# ---------- Surviving the database closing connections (Postgres only) ----------

@pytest.mark.skipif(engine.dialect.name != "postgresql", reason="needs a Postgres test database")
def test_connection_closed_by_the_database_is_replaced():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))  # leaves an open connection waiting in the pool

    # What Neon does when it suspends: close every connection to the database
    admin = create_engine(engine.url, poolclass=NullPool)
    with admin.connect() as connection:
        connection.execute(text(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = current_database() AND pid <> pg_backend_pid()"
        ))
    admin.dispose()

    with engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar() == 1