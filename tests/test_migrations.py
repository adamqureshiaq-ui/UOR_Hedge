"""Alembic migrations: they must build exactly the tables models.py describes, on SQLite and Postgres."""
import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from alembic.util import CommandError
from sqlalchemy import inspect, text

from database import ALEMBIC_INI, BASELINE_REVISION, Base, engine, upgrade_database

ALEMBIC_CONFIG = Config(str(ALEMBIC_INI))
LATEST = ScriptDirectory.from_config(ALEMBIC_CONFIG).get_current_head()


def empty_database():
    """Removes every table, including Alembic's record, as on a brand-new Neon database."""
    Base.metadata.drop_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS alembic_version"))


def current_revision():
    with engine.connect() as connection:
        return MigrationContext.configure(connection).get_current_revision()


def differences_from_models():
    """What `alembic revision --autogenerate` would put in a new migration right now."""
    with engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_type": True})
        return compare_metadata(context, Base.metadata)


# ---------- A brand-new database ----------

def test_migrations_build_exactly_the_tables_in_models():
    # Fails when models.py was changed without adding a migration for it
    empty_database()
    upgrade_database()
    assert differences_from_models() == []


def test_new_database_is_at_the_latest_migration():
    empty_database()
    upgrade_database()
    assert current_revision() == LATEST


# ---------- A database from before migrations (made by create_all, like your local database.db) ----------

def test_database_made_before_migrations_is_upgraded_without_errors():
    # conftest.py has just made every table with create_all, and no Alembic record exists
    upgrade_database()
    assert current_revision() == LATEST

def test_database_made_before_migrations_survives_alembic_check_being_run_first():
    # `alembic check` refuses an un-upgraded database, but leaves behind an empty alembic_version table
    with pytest.raises(CommandError):
        command.check(ALEMBIC_CONFIG)
    upgrade_database()
    assert current_revision() == LATEST

def test_database_made_before_migrations_keeps_its_data():
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO users (id, username, email, hashed_password, cash_balance) "
            "VALUES ('u1', 'alice', 'alice@test.com', 'x', 10000)"
        ))
    upgrade_database()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT username FROM users")).scalar() == "alice"


# ---------- Running again, and undoing ----------

def test_upgrading_twice_is_harmless():
    empty_database()
    upgrade_database()
    upgrade_database()
    assert current_revision() == LATEST


def test_migrations_can_be_undone_back_to_an_empty_database():
    empty_database()
    upgrade_database()
    command.downgrade(ALEMBIC_CONFIG, "base")
    assert inspect(engine).get_table_names() == ["alembic_version"]


def test_baseline_is_the_first_migration():
    assert ScriptDirectory.from_config(ALEMBIC_CONFIG).get_revision(BASELINE_REVISION).down_revision is None