from types import SimpleNamespace
from fastapi.testclient import TestClient
import main

client = TestClient(main.app)


def fake_price(price):
    # Pretend Alpaca answered with this price instead of calling the real API
    return lambda req: {"AAPL": SimpleNamespace(price=price)}


def register_and_login(username):
    client.post("/register", json={"username": username, "email": f"{username}@test.com", "password": "pw123456"})
    resp = client.post("/login", data={"username": username, "password": "pw123456"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_login_rejects_wrong_password():
    register_and_login("bob")
    resp = client.post("/login", data={"username": "bob", "password": "wrong"})
    assert resp.status_code == 401


def test_buy_deducts_cash(monkeypatch):
    monkeypatch.setattr(main.stock_data_client, "get_stock_latest_trade", fake_price(200.0))
    headers = register_and_login("carol")
    resp = client.post("/trade/buy", json={"symbol": "aapl", "quantity": 3}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["remaining_cash"] == 9400.0   # 10,000 − 3 × 200


def test_buy_requires_login():
    resp = client.post("/trade/buy", json={"symbol": "AAPL", "quantity": 1})
    assert resp.status_code == 401