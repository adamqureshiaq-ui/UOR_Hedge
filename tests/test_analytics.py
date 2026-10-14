import numpy as np
import pytest
from helpers import (
    buy,
    client,
    fake_daily_bars,
    register_and_login,
    use_market_prices,
    use_price_history,
)

import market_data


def run(headers, **body):
    return client.post("/analytics/monte-carlo", json=body, headers=headers)


def steady_growth(start, daily_growth, days=60):
    # A stock that rises by exactly the same % every day: no volatility at all
    return [start * daily_growth**i for i in range(days)]


def zigzag(start, step, days=60, up_first=True):
    # A stock that alternates up/down by `step` (in log terms) every day: volatile, but no overall trend
    sign = 1 if up_first else -1
    return [start * np.exp(step * sign * (i % 2)) for i in range(days)]


def test_monte_carlo_requires_login():
    resp = client.post("/analytics/monte-carlo", json={})
    assert resp.status_code == 401


def test_monte_carlo_rejects_empty_portfolio():
    headers = register_and_login("kim")
    resp = run(headers)
    assert resp.status_code == 400


def test_monte_carlo_rejects_too_many_simulations():
    headers = register_and_login("leo")
    resp = run(headers, simulations=1_000_000)
    assert resp.status_code == 422


def test_monte_carlo_steady_growth_compounds_exactly(monkeypatch):
    # $9,000 cash + 10 AAPL at $100. AAPL has risen exactly 1% every day with zero volatility,
    # so every simulated future should be identical: $1,000 × 1.01^5 = $1,051.01 of stock.
    use_market_prices(monkeypatch, {"AAPL": 100.0})
    headers = register_and_login("mia")
    buy(headers, "AAPL", 10)
    use_price_history(monkeypatch, {"AAPL": steady_growth(50.0, 1.01)})

    resp = run(headers, days=5, simulations=100, seed=1)
    assert resp.json()["final_value_percentiles"]["p50"] == pytest.approx(9000 + 1000 * 1.01**5, abs=0.01)


def test_monte_carlo_same_seed_gives_same_result(monkeypatch):
    use_market_prices(monkeypatch, {"AAPL": 100.0})
    headers = register_and_login("nora")
    buy(headers, "AAPL", 10)
    use_price_history(monkeypatch, {"AAPL": zigzag(100.0, 0.02)})

    first = run(headers, days=21, simulations=500, seed=42).json()
    second = run(headers, days=21, simulations=500, seed=42).json()
    assert first == second


def test_monte_carlo_uses_correlation_between_stocks(monkeypatch):
    # Same two volatile stocks, held in equal amounts. When they move in OPPOSITE directions they
    # cancel out (a hedge), so the range of outcomes must be far narrower than when they move TOGETHER.
    use_market_prices(monkeypatch, {"AAPL": 100.0, "MSFT": 100.0})
    headers = register_and_login("omar")
    buy(headers, "AAPL", 10)
    buy(headers, "MSFT", 10)

    def outcome_spread(msft_up_first):
        use_price_history(monkeypatch, {"AAPL": zigzag(100.0, 0.02), "MSFT": zigzag(100.0, 0.02, up_first=msft_up_first)})
        percentiles = run(headers, days=21, simulations=2000, seed=7).json()["final_value_percentiles"]
        return percentiles["p95"] - percentiles["p5"]

    assert outcome_spread(msft_up_first=False) < outcome_spread(msft_up_first=True) / 5


def test_monte_carlo_fetches_history_in_one_request(monkeypatch):
    use_market_prices(monkeypatch, {"AAPL": 100.0, "MSFT": 100.0})
    headers = register_and_login("pia")
    buy(headers, "AAPL", 1)
    buy(headers, "MSFT", 1)

    calls = []
    respond = fake_daily_bars({"AAPL": zigzag(100.0, 0.02), "MSFT": zigzag(100.0, 0.01)})

    def counting_fake(req):
        calls.append(req)
        return respond(req)

    monkeypatch.setattr(market_data.stock_data_client, "get_stock_bars", counting_fake)
    run(headers, seed=1)
    assert len(calls) == 1