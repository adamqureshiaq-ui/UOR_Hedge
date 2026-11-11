"""Loads .env once and exposes every setting the app needs (like Django's settings.py)."""
import os
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

# "production" on Render; anything else (the default) means local development or tests
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Uses SQLite locally. In production this is the Neon PostgreSQL URL.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./database.db")
DEFAULT_JWT_SECRET_KEY = "super-secret-key-change-in-production"
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", DEFAULT_JWT_SECRET_KEY)
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
STARTING_CASH = Decimal("10000.00")  # Paper capital every new member starts with

# Websites allowed to call this API from a browser, comma-separated, e.g. "https://uor-hedge.pages.dev".
# Not needed locally: the Vite dev server forwards /api requests, so the browser only sees one website.
CORS_ORIGINS = [origin.strip().rstrip("/") for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()]

MIN_JWT_SECRET_LENGTH = 32  # HS256 keys shorter than 32 bytes are easier to brute-force (RFC 7518)


def production_settings_problems(jwt_secret_key: str, database_url: str, cors_origins: list[str]) -> list[str]:
    """Everything that would make the deployed app insecure or broken. An empty list means all is well."""
    problems = []
    if jwt_secret_key == DEFAULT_JWT_SECRET_KEY:
        problems.append("JWT_SECRET_KEY is not set, so anyone could forge a login token.")
    elif len(jwt_secret_key) < MIN_JWT_SECRET_LENGTH:
        problems.append(f"JWT_SECRET_KEY must be at least {MIN_JWT_SECRET_LENGTH} characters long.")
    if database_url.startswith("sqlite"):
        problems.append("DATABASE_URL is SQLite, whose file is wiped every time Render restarts the server.")
    if not cors_origins:
        problems.append("CORS_ORIGINS is empty, so the website would not be allowed to call the API.")
    elif "*" in cors_origins:
        problems.append('CORS_ORIGINS must list your website, not "*" (which would let any website call the API).')
    return problems


if ENVIRONMENT == "production":
    _problems = production_settings_problems(JWT_SECRET_KEY, DATABASE_URL, CORS_ORIGINS)
    if _problems:
        raise RuntimeError("Refusing to start in production:\n- " + "\n- ".join(_problems))