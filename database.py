from sqlalchemy import create_engine
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

def get_db():
    """Provides a database session to FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()