import market_data
from helpers import use_market_prices, get_shares_owned, buy, register_and_login, client, fake_prices, fake_quotes


def test_portfolio_empty_equity_is_cash():
    headers = register_and_login("frank")
    resp = client.get("/portfolio", headers=headers)
    assert resp.json()["total_equity"] == 10000.0


def test_portfolio_total_equity_uses_live_prices(monkeypatch):
    headers = register_and_login("grace")
    # Buy at today's prices: 5 × $100 + 2 × $200 = $900 spent → $9,100 cash
    use_market_prices(monkeypatch, {"AAPL": 100.0, "MSFT": 200.0})
    buy(headers, "AAPL", 5)
    buy(headers, "MSFT", 2)
    # Prices move: holdings now worth 5 × $110 + 2 × $250 = $1,050
    use_market_prices(monkeypatch, {"AAPL": 110.0, "MSFT": 250.0})
    resp = client.get("/portfolio", headers=headers)
    assert resp.json()["total_equity"] == 10150.0   # $9,100 cash + $1,050


def test_portfolio_fetches_all_prices_in_one_request(monkeypatch):
    headers = register_and_login("heidi")
    use_market_prices(monkeypatch, {"AAPL": 100.0, "MSFT": 200.0})
    buy(headers, "AAPL", 1)
    buy(headers, "MSFT", 1)

    calls = []

    def counting_fake(req):
        calls.append(req)
        return fake_prices({"AAPL": 100.0, "MSFT": 200.0})(req)

    monkeypatch.setattr(market_data.stock_data_client, "get_stock_latest_trade", counting_fake)
    client.get("/portfolio", headers=headers)
    assert len(calls) == 1


def test_portfolio_requires_login():
    resp = client.get("/portfolio")
    assert resp.status_code == 401
    