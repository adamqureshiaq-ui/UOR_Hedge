from decimal import Decimal

from helpers import (
    buy,
    client,
    get_cash_balance,
    get_shares_owned,
    register_and_login,
    sell,
    use_market_prices,
)


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


    # ---------- Exact money and share arithmetic ----------

def test_sell_entire_fractional_position(monkeypatch):
    # With floats, 0.3 - 0.1 left 0.19999999999999998 shares, so selling the last 0.2 was refused
    use_market_prices(monkeypatch, {"AAPL": 100.0})
    headers = register_and_login("fran")
    buy(headers, "AAPL", 0.3)
    sell(headers, "AAPL", 0.1)
    resp = sell(headers, "AAPL", 0.2)
    assert resp.status_code == 200


def test_selling_everything_removes_the_holding(monkeypatch):
    use_market_prices(monkeypatch, {"AAPL": 100.0})
    headers = register_and_login("gus")
    buy(headers, "AAPL", 0.3)
    sell(headers, "AAPL", 0.1)
    sell(headers, "AAPL", 0.2)
    assert get_shares_owned("gus", "AAPL") == 0


def test_trade_cost_is_rounded_to_the_cent(monkeypatch):
    # 0.333333 shares × $100 = $33.3333, which is charged as $33.33 (so $9,966.67 is left, not $9,966.6667)
    use_market_prices(monkeypatch, {"AAPL": 100.0})
    headers = register_and_login("hal")
    buy(headers, "AAPL", 0.333333)
    assert get_cash_balance("hal") == Decimal("9966.67")


def test_many_small_trades_keep_cash_exact(monkeypatch):
    # Ten buys of $1.01 must leave exactly $9,989.90, with no tiny float error building up
    use_market_prices(monkeypatch, {"AAPL": 10.1})
    headers = register_and_login("ida")
    for _ in range(10):
        buy(headers, "AAPL", 0.1)
    assert get_cash_balance("ida") == Decimal("9989.90")


def test_quantity_with_more_than_six_decimal_places_is_rejected(monkeypatch):
    use_market_prices(monkeypatch, {"AAPL": 100.0})
    headers = register_and_login("jo")
    resp = buy(headers, "AAPL", 0.1234567)
    assert resp.status_code == 422


def test_insufficient_shares_message_shows_a_clean_number(monkeypatch):
    use_market_prices(monkeypatch, {"AAPL": 100.0})
    headers = register_and_login("kai")
    buy(headers, "AAPL", 2)
    resp = sell(headers, "AAPL", 5)
    assert resp.json()["detail"] == "Insufficient shares to sell. You have 2 shares of AAPL."