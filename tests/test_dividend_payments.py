"""The daily job's dividend handling, step 2: paying on the pay date, and counting what's owed in equity."""
from datetime import timedelta
from decimal import Decimal

from helpers import (
    alpaca_dividend,
    buy,
    client,
    get_cash_balance,
    get_pending_dividends,
    get_transactions,
    register_and_login,
    run_corporate_actions,
    use_corporate_actions,
    use_market_prices,
)

import corporate_actions

TODAY = corporate_actions.market_today()
EX_DATE = TODAY + timedelta(days=1)
PAY_DAY = TODAY + timedelta(days=21)


def owed_a_dividend(monkeypatch, quantity=10, rate=0.25):
    """alice bought `quantity` AAPL at $100 today ($9,000 cash left), and the ex-date has passed: she is owed."""
    use_market_prices(monkeypatch, {"AAPL": 100.0})
    headers = register_and_login("alice")
    buy(headers, "AAPL", quantity)
    use_corporate_actions(monkeypatch, alpaca_dividend("AAPL", rate, EX_DATE.isoformat(), PAY_DAY.isoformat()))
    run_corporate_actions(EX_DATE)
    return headers


# ---------- Paying ----------

def test_dividend_is_paid_into_cash_on_the_pay_date(monkeypatch):
    owed_a_dividend(monkeypatch, quantity=10, rate=0.25)
    run_corporate_actions(PAY_DAY)
    assert get_cash_balance("alice") == Decimal("9002.50")


def test_dividend_is_not_paid_before_the_pay_date(monkeypatch):
    owed_a_dividend(monkeypatch)
    run_corporate_actions(PAY_DAY - timedelta(days=1))
    assert get_cash_balance("alice") == Decimal("9000.00")


def test_paid_dividend_is_marked_paid(monkeypatch):
    owed_a_dividend(monkeypatch)
    run_corporate_actions(PAY_DAY)
    assert get_pending_dividends("alice")[0].paid_at is not None


def test_running_twice_on_the_pay_date_pays_once(monkeypatch):
    owed_a_dividend(monkeypatch, quantity=10, rate=0.25)
    run_corporate_actions(PAY_DAY)
    run_corporate_actions(PAY_DAY)
    assert get_cash_balance("alice") == Decimal("9002.50")


def test_payment_is_recorded_in_transaction_history(monkeypatch):
    owed_a_dividend(monkeypatch, quantity=10, rate=0.25)
    run_corporate_actions(PAY_DAY)
    assert [payment.total_amount for payment in get_transactions("alice", "DIVIDEND")] == [Decimal("2.50")]


def test_late_run_records_and_pays_in_one_go(monkeypatch):
    # The job didn't run between the ex-date and the pay date (e.g. the server was off)
    use_market_prices(monkeypatch, {"AAPL": 100.0})
    buy(register_and_login("alice"), "AAPL", 10)
    use_corporate_actions(monkeypatch, alpaca_dividend("AAPL", 0.25, EX_DATE.isoformat(), PAY_DAY.isoformat()))
    run_corporate_actions(PAY_DAY + timedelta(days=3))
    assert get_cash_balance("alice") == Decimal("9002.50")


def test_payment_does_not_count_as_shares_for_a_later_dividend(monkeypatch):
    owed_a_dividend(monkeypatch, quantity=10)
    run_corporate_actions(PAY_DAY)  # pays the first dividend
    next_ex_date = PAY_DAY + timedelta(days=1)
    use_corporate_actions(monkeypatch, alpaca_dividend("AAPL", 0.25, next_ex_date.isoformat(), PAY_DAY.isoformat()))
    run_corporate_actions(next_ex_date)
    assert get_pending_dividends("alice")[-1].shares == 10


def test_report_names_each_payment(monkeypatch):
    owed_a_dividend(monkeypatch, quantity=10, rate=0.25)
    assert run_corporate_actions(PAY_DAY) == [f"AAPL: paid $2.50 dividend (ex {EX_DATE}) to 1 member(s)"]


# ---------- Counting what's owed in equity ----------

def test_portfolio_shows_dividends_owed(monkeypatch):
    headers = owed_a_dividend(monkeypatch, quantity=10, rate=0.25)
    assert client.get("/portfolio", headers=headers).json()["pending_dividends"] == 2.5


def test_portfolio_equity_includes_dividends_owed(monkeypatch):
    headers = owed_a_dividend(monkeypatch, quantity=10, rate=0.25)
    # $9,000 cash + 10 x $100 + $2.50 owed
    assert client.get("/portfolio", headers=headers).json()["total_equity"] == 10002.5


def test_portfolio_shows_nothing_owed_once_paid(monkeypatch):
    headers = owed_a_dividend(monkeypatch)
    run_corporate_actions(PAY_DAY)
    assert client.get("/portfolio", headers=headers).json()["pending_dividends"] == 0


def test_payment_does_not_change_equity(monkeypatch):
    headers = owed_a_dividend(monkeypatch)
    before = client.get("/portfolio", headers=headers).json()["total_equity"]
    run_corporate_actions(PAY_DAY)  # the money moves from "owed" to cash
    assert client.get("/portfolio", headers=headers).json()["total_equity"] == before


def test_leaderboard_equity_includes_dividends_owed(monkeypatch):
    headers = owed_a_dividend(monkeypatch, quantity=10, rate=0.25)
    entries = client.get("/leaderboard", headers=headers).json()["entries"]
    assert entries[0]["total_equity"] == 10002.5