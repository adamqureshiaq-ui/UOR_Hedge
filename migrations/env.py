"""How Alembic connects to the database. Runs for every `alembic ...` command and on server startup."""
from logging.config import fileConfig

from alembic import context

import models  # noqa: F401  – registers every table on Base.metadata
from database import Base, engine

config = context.config

# Logging settings from alembic.ini. disable_existing_loggers=False so that running migrations on
# server startup doesn't silence uvicorn's and the app's own log messages.
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)


def run_migrations() -> None:
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=Base.metadata,  # what autogenerate compares the database against
            # SQLite can't change or drop most columns in place; "batch" mode copies the table instead
            render_as_batch=connection.dialect.name == "sqlite",
            compare_type=True,  # also notice column type changes, e.g. Numeric(14, 2) -> Numeric(18, 2)
        )
        with context.begin_transaction():
            context.run_migrations()


run_migrations()