"""Shared test helpers: the test client, user setup, and fakes for Alpaca's market data."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

import main
import market_data
import models
from database import SessionLocal

client = TestClient(main.app)


# ---------- Users ----------

def register_and_login(username):
    """Registers a member and returns the Authorization header for their JWT."""
    client.post("/register", json={"username": username, "email": f"{username}@test.com", "password": "pw123456"})
    resp = client.post("/login", data={"username": username, "password": "pw123456"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ---------- Trading shortcuts (for setting up a test, not for checking results) ----------

def buy(headers, symbol, quantity):
    return client.post("/trade/buy", json={"symbol": symbol, "quantity": quantity}, headers=headers)


def sell(headers, symbol, quantity):
    return client.post("/trade/sell", json={"symbol": symbol, "quantity": quantity}, headers=headers)


# ---------- Fake Alpaca market data ----------

def fake_prices(prices):
    """Fake last-trade response, e.g. {"AAPL": 100.0, "MSFT": 200.0}."""
    return lambda req: {symbol: SimpleNamespace(price=price) for symbol, price in prices.items()}


def fake_quotes(prices):
    """Fake live-quote response where bid = ask = the given price."""
    return lambda req: {symbol: SimpleNamespace(bid_price=price, ask_price=price) for symbol, price in prices.items()}


def use_market_prices(monkeypatch, prices):
    """Fakes every live-price call to Alpaca (last trade, bid and ask) with the same prices."""
    monkeypatch.setattr(market_data.stock_data_client, "get_stock_latest_trade", fake_prices(prices))
    monkeypatch.setattr(market_data.stock_data_client, "get_stock_latest_quote", fake_quotes(prices))


# ---------- Reading the database directly ----------

def get_shares_owned(username, symbol):
    """How many shares of `symbol` the user holds, read straight from the database."""
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.username == username).first()
        holding = db.query(models.Portfolio).filter(
            models.Portfolio.user_id == user.id,
            models.Portfolio.symbol == symbol,
        ).first()
        return holding.quantity if holding else 0
    finally:
        db.close()


def fake_daily_bars(closes_by_symbol):
    """Fake historical-bars response: {"AAPL": [100.0, 101.0, ...]} -> one bar per day, oldest first."""
    first_day = datetime(2025, 1, 1, tzinfo=timezone.utc)

    def respond(req):
        return {
            symbol: [SimpleNamespace(timestamp=first_day + timedelta(days=i), close=close) for i, close in enumerate(closes)]
            for symbol, closes in closes_by_symbol.items()
        }
    return respond


def use_price_history(monkeypatch, closes_by_symbol):
    """Fakes Alpaca's historical daily bars with the given closing prices."""
    monkeypatch.setattr(market_data.stock_data_client, "get_stock_bars", fake_daily_bars(closes_by_symbol))