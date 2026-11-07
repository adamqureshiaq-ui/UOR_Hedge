"""Shared test helpers: the test client, user setup, and fakes for Alpaca's market data."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

import corporate_actions
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


def use_stock_list(monkeypatch, stocks):
    """Fakes Alpaca's list of stocks: [("AAPL", "Apple Inc."), ...]. Add False as a third item for an untradable stock."""
    assets = [
        {"symbol": symbol, "name": name, "exchange": "NASDAQ", "tradable": rest[0] if rest else True}
        for symbol, name, *rest in stocks
    ]
    monkeypatch.setattr(market_data.trading_client, "get_all_assets", lambda filter=None: assets)


def get_cash_balance(username):
    """The user's cash exactly as stored in the database."""
    db = SessionLocal()
    try:
        return db.query(models.User).filter(models.User.username == username).first().cash_balance
    finally:
        db.close()


# ---------- Fake Alpaca corporate actions (splits and dividends) ----------

def alpaca_split(symbol, old_rate, new_rate, ex_date, action_id=None):
    """One split as Alpaca returns it. A 4-for-1 split is old_rate=1, new_rate=4; 1-for-10 is old_rate=10, new_rate=1."""
    kind = "forward_splits" if new_rate > old_rate else "reverse_splits"
    return kind, {
        "id": action_id or f"split-{symbol}-{ex_date}",
        "symbol": symbol,
        "old_rate": old_rate,
        "new_rate": new_rate,
        "ex_date": ex_date,
        "process_date": ex_date,
    }


def alpaca_dividend(symbol, rate, ex_date, payable_date=None, action_id=None):
    """One cash dividend as Alpaca returns it: `rate` dollars per share."""
    item = {
        "id": action_id or f"dividend-{symbol}-{ex_date}",
        "symbol": symbol,
        "rate": rate,
        "special": False,
        "foreign": False,
        "ex_date": ex_date,
        "process_date": ex_date,
    }
    if payable_date:
        item["payable_date"] = payable_date
    return "cash_dividends", item


def use_corporate_actions(monkeypatch, *actions):
    """Fakes Alpaca's corporate actions with alpaca_split(...) / alpaca_dividend(...) entries.

    Returns a list that records each request made, so a test can check what was asked for.
    """
    grouped = {}
    for kind, item in actions:
        grouped.setdefault(kind, []).append(item)
    requests_made = []

    def respond(request):
        requests_made.append(request)
        return grouped

    monkeypatch.setattr(market_data.corporate_actions_client, "get_corporate_actions", respond)
    return requests_made



# ---------- Corporate actions job ----------

def run_corporate_actions(today):
    """Runs the daily splits job as if it were `today` (a date in New York)."""
    db = SessionLocal()
    try:
        return corporate_actions.apply_corporate_actions(db, today=today)
    finally:
        db.close()


def move_trades_to(username, moment):
    """Re-dates every trade the user has made so far, e.g. to before a split took effect."""
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.username == username).first()
        db.query(models.Transaction).filter(models.Transaction.user_id == user.id).update({"timestamp": moment})
        db.commit()
    finally:
        db.close()


def get_average_buy_price(username, symbol):
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.username == username).first()
        holding = db.query(models.Portfolio).filter(
            models.Portfolio.user_id == user.id,
            models.Portfolio.symbol == symbol,
        ).first()
        return holding.average_buy_price
    finally:
        db.close()


def get_transactions(username, order_type):
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.username == username).first()
        return db.query(models.Transaction).filter(
            models.Transaction.user_id == user.id,
            models.Transaction.order_type == order_type,
        ).all()
    finally:
        db.close()


def get_pending_dividends(username):
    """Every dividend entitlement recorded for the user, oldest ex-date first."""
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.username == username).first()
        return db.query(models.PendingDividend).filter(
            models.PendingDividend.user_id == user.id
        ).order_by(models.PendingDividend.ex_date).all()
    finally:
        db.close()