import os

import pytest

import market_data
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


@pytest.fixture(autouse=True)
def block_real_alpaca(monkeypatch):
    """Fail loudly if a test reaches the real Alpaca API instead of a fake."""
    def refuse(method_name):
        def fail(request):
            raise AssertionError(f"Test called the real Alpaca API ({method_name}). Fake it, e.g. with use_market_prices().")
        return fail

    for method_name in ("get_stock_latest_trade", "get_stock_latest_quote", "get_stock_bars"):
        monkeypatch.setattr(market_data.stock_data_client, method_name, refuse(method_name))

    monkeypatch.setattr(market_data.trading_client, "get_all_assets", refuse("get_all_assets"))

    # The stock list is cached in memory between requests; start every test without it
    market_data.clear_stock_list_cache()