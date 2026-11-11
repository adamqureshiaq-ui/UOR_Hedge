"""Settings for the deployed app: refusing unsafe settings, and which websites may call the API."""
import os
import subprocess
import sys
from pathlib import Path

from config import MIN_JWT_SECRET_LENGTH, production_settings_problems

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOOD_SECRET = "x" * MIN_JWT_SECRET_LENGTH
NEON_URL = "postgresql://user:password@ep-example.eu-west-2.aws.neon.tech/neondb?sslmode=require"
WEBSITE = "https://uor-hedge.pages.dev"


def problems(jwt_secret_key=GOOD_SECRET, database_url=NEON_URL, cors_origins=(WEBSITE,)):
    return production_settings_problems(jwt_secret_key, database_url, list(cors_origins))


def run_python(code, **settings):
    """Runs `code` in a fresh Python process with these extra environment variables (settings are read
    once at import, so a new process is the only way to try different ones)."""
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        env={**os.environ, **settings},
        capture_output=True,
        text=True,
    )


# ---------- What counts as unsafe in production ----------

def test_good_production_settings_have_no_problems():
    assert problems() == []


def test_default_jwt_secret_is_a_problem():
    assert len(problems(jwt_secret_key="super-secret-key-change-in-production")) == 1


def test_short_jwt_secret_is_a_problem():
    assert len(problems(jwt_secret_key="x" * (MIN_JWT_SECRET_LENGTH - 1))) == 1


def test_sqlite_database_is_a_problem():
    assert len(problems(database_url="sqlite:///./database.db")) == 1


def test_no_allowed_website_is_a_problem():
    assert len(problems(cors_origins=())) == 1


def test_allowing_every_website_is_a_problem():
    assert len(problems(cors_origins=("*",))) == 1


# ---------- Starting up ----------

def test_production_refuses_to_start_with_unsafe_settings():
    result = run_python("import config", ENVIRONMENT="production", JWT_SECRET_KEY="too-short")
    assert "Refusing to start in production" in result.stderr


def test_production_starts_with_safe_settings():
    result = run_python(
        "import config",
        ENVIRONMENT="production", JWT_SECRET_KEY=GOOD_SECRET, DATABASE_URL=NEON_URL, CORS_ORIGINS=WEBSITE,
    )
    assert result.returncode == 0


def test_allowed_websites_are_read_from_a_comma_separated_list():
    result = run_python("import config; print(config.CORS_ORIGINS)", CORS_ORIGINS=" https://a.pages.dev/ ,https://b.org")
    assert result.stdout.strip() == "['https://a.pages.dev', 'https://b.org']"


# ---------- Which websites may call the API from a browser (CORS) ----------

PREFLIGHT = """
from fastapi.testclient import TestClient
import main
response = TestClient(main.app).options("/portfolio", headers={
    "Origin": "%s",
    "Access-Control-Request-Method": "GET",
    "Access-Control-Request-Headers": "authorization",
})
print(response.headers.get("access-control-allow-origin"))
"""


def test_browser_on_the_allowed_website_may_call_the_api():
    result = run_python(PREFLIGHT % WEBSITE, CORS_ORIGINS=WEBSITE)
    assert result.stdout.strip() == WEBSITE


def test_browser_on_another_website_may_not_call_the_api():
    result = run_python(PREFLIGHT % "https://evil.example", CORS_ORIGINS=WEBSITE)
    assert result.stdout.strip() == "None"