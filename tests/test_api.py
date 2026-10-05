from types import SimpleNamespace

from fastapi.testclient import TestClient

from database import SessionLocal

import main
import market_data
import models

client = TestClient(main.app)


### HELPER FUNCTIONS ###
def fake_price(price):
    # Pretend Alpaca answered with this price instead of calling the real API
    return lambda req: {"AAPL": SimpleNamespace(price=price)}


def register_and_login(username):
    client.post("/register", json={"username": username, "email": f"{username}@test.com", "password": "pw123456"})
    resp = client.post("/login", data={"username": username, "password": "pw123456"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def get_shares_owned(username, symbol):
    """Reads the database directly to see how many shares a user holds."""
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


### TESTS ###
def test_login_rejects_wrong_password():
    register_and_login("bob")
    resp = client.post("/login", data={"username": "bob", "password": "wrong"})
    assert resp.status_code == 401


def test_buy_deducts_cash(monkeypatch):
    monkeypatch.setattr(market_data.stock_data_client, "get_stock_latest_trade", fake_price(200.0))
    headers = register_and_login("carol")
    resp = client.post("/trade/buy", json={"symbol": "aapl", "quantity": 3}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["remaining_cash"] == 9400.0   # 10,000 − 3 × 200


def test_buy_requires_login():
    resp = client.post("/trade/buy", json={"symbol": "AAPL", "quantity": 1})
    assert resp.status_code == 401


def test_sell_rejects_insufficient_shares(monkeypatch):
    monkeypatch.setattr(market_data.stock_data_client, "get_stock_latest_trade", fake_price(150.0))
    headers = register_and_login("dave")
    # Dave has no shares of AAPL, so this should fail
    resp = client.post("/trade/sell", json={"symbol": "AAPL", "quantity": 1}, headers=headers)
    assert resp.status_code == 400
    assert "Insufficient shares" in resp.json()["detail"]


def test_sell_requires_login():
    resp = client.post("/trade/sell", json={"symbol": "AAPL", "quantity": 1})
    assert resp.status_code == 401


def test_sell_number_of_shares(monkeypatch):
    monkeypatch.setattr(market_data.stock_data_client, "get_stock_latest_trade", fake_price(100.0))
    headers = register_and_login("eve")
    # First, buy 5 shares of AAPL
    client.post("/trade/buy", json={"symbol": "AAPL", "quantity": 5}, headers=headers)
    # Now sell 2 shares of AAPL
    resp = client.post("/trade/sell", json={"symbol": "AAPL", "quantity": 2}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["quantity"] == 2


def test_sell_deducts_shares(monkeypatch):
    monkeypatch.setattr(market_data.stock_data_client, "get_stock_latest_trade", fake_price(100.0))
    headers = register_and_login("eve")
    # First, buy 5 shares of AAPL
    client.post("/trade/buy", json={"symbol": "AAPL", "quantity": 5}, headers=headers)
    # Now sell 2 shares of AAPL
    resp = client.post("/trade/sell", json={"symbol": "AAPL", "quantity": 2}, headers=headers)
    # TODO: switch to GET /portfolio once feature/portfolio-valuation is merged
    assert get_shares_owned("eve", "AAPL") == 3  # 5 - 2 = 3 shares remaining


def test_sell_increases_cash(monkeypatch):
    monkeypatch.setattr(market_data.stock_data_client, "get_stock_latest_trade", fake_price(100.0))
    headers = register_and_login("frank")
    # First, buy 5 shares of AAPL at $100 each
    client.post("/trade/buy", json={"symbol": "AAPL", "quantity": 5}, headers=headers)
    # Now sell 2 shares of AAPL at $100 each
    resp = client.post("/trade/sell", json={"symbol": "AAPL", "quantity": 2}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["remaining_cash"] == 9700.0  # 10,000 - (5*100) + (2*100) = 9700