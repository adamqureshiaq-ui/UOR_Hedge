from helpers import client, register_and_login, use_market_prices, get_shares_owned



### TESTS ###
def test_login_rejects_wrong_password():
    register_and_login("bob")
    resp = client.post("/login", data={"username": "bob", "password": "wrong"})
    assert resp.status_code == 401


def test_buy_deducts_cash(monkeypatch):
    use_market_prices(monkeypatch, {"AAPL": 200.0})
    headers = register_and_login("carol")
    resp = client.post("/trade/buy", json={"symbol": "AAPL", "quantity": 3}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["remaining_cash"] == 9400.0   # 10,000 − 3 × 200


def test_buy_requires_login():
    resp = client.post("/trade/buy", json={"symbol": "AAPL", "quantity": 1})
    assert resp.status_code == 401


def test_sell_rejects_insufficient_shares(monkeypatch):
    use_market_prices(monkeypatch, {"AAPL": 150.0})
    headers = register_and_login("dave")
    # Dave has no shares of AAPL, so this should fail
    resp = client.post("/trade/sell", json={"symbol": "AAPL", "quantity": 1}, headers=headers)
    assert resp.status_code == 400
    assert "Insufficient shares" in resp.json()["detail"]


def test_sell_requires_login():
    resp = client.post("/trade/sell", json={"symbol": "AAPL", "quantity": 1})
    assert resp.status_code == 401


def test_sell_number_of_shares(monkeypatch):
    use_market_prices(monkeypatch, {"AAPL": 100.0})
    headers = register_and_login("eve")
    # First, buy 5 shares of AAPL
    client.post("/trade/buy", json={"symbol": "AAPL", "quantity": 5}, headers=headers)
    # Now sell 2 shares of AAPL
    resp = client.post("/trade/sell", json={"symbol": "AAPL", "quantity": 2}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["quantity"] == 2


def test_sell_deducts_shares(monkeypatch):
    use_market_prices(monkeypatch, {"AAPL": 100.0})
    headers = register_and_login("eve")
    # First, buy 5 shares of AAPL
    client.post("/trade/buy", json={"symbol": "AAPL", "quantity": 5}, headers=headers)
    # Now sell 2 shares of AAPL
    client.post("/trade/sell", json={"symbol": "AAPL", "quantity": 2}, headers=headers)
    # TODO: switch to GET /portfolio once feature/portfolio-valuation is merged
    assert get_shares_owned("eve", "AAPL") == 3  # 5 - 2 = 3 shares remaining


def test_sell_increases_cash(monkeypatch):
    use_market_prices(monkeypatch, {"AAPL": 100.0})
    headers = register_and_login("frank")
    # First, buy 5 shares of AAPL at $100 each
    client.post("/trade/buy", json={"symbol": "AAPL", "quantity": 5}, headers=headers)
    # Now sell 2 shares of AAPL at $100 each
    resp = client.post("/trade/sell", json={"symbol": "AAPL", "quantity": 2}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["remaining_cash"] == 9700.0  # 10,000 - (5*100) + (2*100) = 9700