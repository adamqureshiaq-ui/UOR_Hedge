from helpers import client, register_and_login, use_stock_list

import market_data

STOCKS = [
    ("AAPL", "Apple Inc. Common Stock"),
    ("APP", "AppLovin Corporation Class A Common Stock"),
    ("APPN", "Appian Corporation Class A Common Stock"),
    ("MSFT", "Microsoft Corporation Common Stock"),
    ("SFTW", "Software Acquisition Group Inc"),
]


def search(headers, q, **params):
    return client.get("/market/search", params={"q": q, **params}, headers=headers)


def symbols(resp):
    return [stock["symbol"] for stock in resp.json()]


def test_search_requires_login():
    resp = client.get("/market/search", params={"q": "apple"})
    assert resp.status_code == 401


def test_search_ranks_ticker_matches_before_name_matches(monkeypatch):
    use_stock_list(monkeypatch, STOCKS)
    resp = search(register_and_login("vic"), "app")
    # exact ticker APP, then ticker starting with APP (APPN), then a name word starting with "app" (Apple)
    assert symbols(resp) == ["APP", "APPN", "AAPL"]


def test_search_finds_company_by_name(monkeypatch):
    use_stock_list(monkeypatch, STOCKS)
    resp = search(register_and_login("wes"), "microsoft")
    assert symbols(resp) == ["MSFT"]


def test_search_matches_inside_a_name_last(monkeypatch):
    use_stock_list(monkeypatch, STOCKS)
    resp = search(register_and_login("xena"), "soft")
    # "Software" starts with "soft"; "Microsoft" only contains it in the middle of the word
    assert symbols(resp) == ["SFTW", "MSFT"]


def test_search_returns_empty_list_when_nothing_matches(monkeypatch):
    use_stock_list(monkeypatch, STOCKS)
    resp = search(register_and_login("yara"), "zzzz")
    assert resp.json() == []


def test_search_hides_untradable_stocks(monkeypatch):
    use_stock_list(monkeypatch, [("AAPL", "Apple Inc."), ("APLE", "Apple Hospitality REIT", False)])
    resp = search(register_and_login("zack"), "apple")
    assert symbols(resp) == ["AAPL"]


def test_search_respects_limit(monkeypatch):
    use_stock_list(monkeypatch, STOCKS)
    resp = search(register_and_login("abby"), "corporation", limit=2)
    assert len(resp.json()) == 2


def test_search_rejects_empty_query():
    resp = search(register_and_login("ben"), "")
    assert resp.status_code == 422


def test_search_downloads_stock_list_only_once(monkeypatch):
    calls = []

    def counting_fake(filter=None):
        calls.append(filter)
        return []

    monkeypatch.setattr(market_data.trading_client, "get_all_assets", counting_fake)
    headers = register_and_login("cleo")
    search(headers, "apple")
    search(headers, "microsoft")
    assert len(calls) == 1