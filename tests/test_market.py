from types import SimpleNamespace

from helpers import client, fake_prices, register_and_login

import market_data


def use_live_prices(monkeypatch, last_trade, bid, ask):
    """Fakes AAPL's last trade and a quote with a real bid/ask spread."""
    monkeypatch.setattr(market_data.stock_data_client, "get_stock_latest_trade", fake_prices({"AAPL": last_trade}))
    monkeypatch.setattr(market_data.stock_data_client, "get_stock_latest_quote",
                        lambda req: {"AAPL": SimpleNamespace(bid_price=bid, ask_price=ask)})


def get_quote(headers, symbol):
    return client.get(f"/market/quote/{symbol}", headers=headers)


def test_quote_requires_login():
    resp = client.get("/market/quote/AAPL")
    assert resp.status_code == 401


def test_quote_returns_bid_ask_and_last_trade(monkeypatch):
    use_live_prices(monkeypatch, last_trade=150.00, bid=149.95, ask=150.05)
    resp = get_quote(register_and_login("quinn"), "AAPL")
    assert resp.json() == {
        "symbol": "AAPL",
        "last_trade_price": 150.00,
        "bid_price": 149.95,
        "ask_price": 150.05,
        "spread": 0.10,
    }


def test_quote_accepts_lowercase_symbol(monkeypatch):
    use_live_prices(monkeypatch, last_trade=150.00, bid=149.95, ask=150.05)
    resp = get_quote(register_and_login("rosa"), "aapl")
    assert resp.json()["symbol"] == "AAPL"


def test_quote_when_market_closed_shows_last_trade_only(monkeypatch):
    use_live_prices(monkeypatch, last_trade=150.00, bid=0.0, ask=0.0)
    resp = get_quote(register_and_login("sam"), "AAPL")
    assert (resp.json()["bid_price"], resp.json()["ask_price"]) == (None, None)


def test_quote_unknown_symbol_returns_400(monkeypatch):
    monkeypatch.setattr(market_data.stock_data_client, "get_stock_latest_trade", fake_prices({}))
    resp = get_quote(register_and_login("tara"), "ZZZZZ")
    assert resp.status_code == 400


def test_quote_rejects_malformed_symbol():
    resp = get_quote(register_and_login("uma"), "AAPL123")
    assert resp.status_code == 422