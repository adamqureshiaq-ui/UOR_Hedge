from helpers import buy, client, fake_prices, register_and_login, use_market_prices

import market_data


def test_leaderboard_ranks_by_total_equity(monkeypatch):
    use_market_prices(monkeypatch, {"AAPL": 100.0, "MSFT": 100.0})
    buy(register_and_login("alice"), "AAPL", 10)   # AAPL will rise
    headers = register_and_login("bob")            # bob keeps all cash
    buy(register_and_login("carol"), "MSFT", 10)   # MSFT will fall
    use_market_prices(monkeypatch, {"AAPL": 150.0, "MSFT": 50.0})

    resp = client.get("/leaderboard", headers=headers)
    assert [entry["username"] for entry in resp.json()["entries"]] == ["alice", "bob", "carol"]


def test_leaderboard_tied_members_share_rank():
    register_and_login("dave")
    headers = register_and_login("erin")
    resp = client.get("/leaderboard", headers=headers)
    assert [entry["rank"] for entry in resp.json()["entries"]] == [1, 1]


def test_leaderboard_reports_my_rank(monkeypatch):
    use_market_prices(monkeypatch, {"AAPL": 100.0})
    buy(register_and_login("frank"), "AAPL", 10)
    headers = register_and_login("grace")
    use_market_prices(monkeypatch, {"AAPL": 150.0})

    resp = client.get("/leaderboard", headers=headers)
    assert resp.json()["my_rank"] == 2


def test_leaderboard_only_shows_public_fields():
    headers = register_and_login("heidi")
    resp = client.get("/leaderboard", headers=headers)
    assert set(resp.json()["entries"][0]) == {"rank", "username", "total_equity", "return_percent"}


def test_leaderboard_fetches_all_prices_in_one_request(monkeypatch):
    use_market_prices(monkeypatch, {"AAPL": 100.0, "MSFT": 100.0})
    buy(register_and_login("ivan"), "AAPL", 1)
    headers = register_and_login("judy")
    buy(headers, "MSFT", 1)

    calls = []

    def counting_fake(req):
        calls.append(req)
        return fake_prices({"AAPL": 100.0, "MSFT": 100.0})(req)

    monkeypatch.setattr(market_data.stock_data_client, "get_stock_latest_trade", counting_fake)
    client.get("/leaderboard", headers=headers)
    assert len(calls) == 1


def test_leaderboard_requires_login():
    resp = client.get("/leaderboard")
    assert resp.status_code == 401