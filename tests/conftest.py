import os

import pytest

import models  # noqa: F401  – registers the tables on Base.metadata
from database import Base, engine


@pytest.fixture(autouse=True)
def fresh_database():
    """Give every test an empty database."""
    if "test" not in os.getenv("DATABASE_URL", ""):
        pytest.exit("Refusing to wipe a non-test database. Set DATABASE_URL to a test database.")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield