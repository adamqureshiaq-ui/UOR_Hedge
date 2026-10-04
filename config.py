"""Loads .env once and exposes every setting the app needs (like Django's settings.py)."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

# Uses SQLite locally. When deploying, replace this string with your PostgreSQL URL!
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./database.db")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-key-change-in-production")
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")