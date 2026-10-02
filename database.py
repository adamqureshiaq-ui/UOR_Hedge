import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Uses SQLite locally. When deploying, replace this string with your PostgreSQL URL!
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./database.db")

# SQLite needs a special check; PostgreSQL does not
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Provides a database session to FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

