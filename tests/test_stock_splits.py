"""The daily job's stock-split handling: python -m corporate_actions."""
from datetime import date, datetime, timedelta
from decimal import Decimal

from helpers import (
    alpaca_split,
    buy,
    get_average_buy_price,
    get_cash_balance,
    get_shares_owned,
    get_transactions,
    move_trades_to,
    register_and_login,
    run_corporate_actions,
    sell,
    use_corporate_actions,
    use_market_prices,
)

import corporate_actions
from market_data import MarketDataError

TODAY = corporate_actions.market_today()
TOMORROW = TODAY + timedelta(days=1)


def holder(monkeypatch, quantity=10, price=100.0, symbol="AAPL"):
    """A member who bought `quantity` shares just now (so before any split dated tomorrow)."""
    use_market_prices(monkeypatch, {symbol: price})
    headers = register_and_login("alice")
    buy(headers, symbol, quantity)
    return headers


def holder_before_today(monkeypatch, quantity=10, price=100.0):
    """A member whose shares were bought before today's market day began, so a split dated today applies."""
    headers = holder(monkeypatch, quantity, price)
    move_trades_to("alice", corporate_actions.start_of_market_day(TODAY) - timedelta(hours=1))
    return headers


# ---------- What a split does ----------

def test_forward_split_multiplies_shares(monkeypatch):
    holder(monkeypatch, quantity=10)
    use_corporate_actions(monkeypatch, alpaca_split("AAPL", 1, 4, TOMORROW.isoformat()))
    run_corporate_actions(TOMORROW)
    assert get_shares_owned("alice", "AAPL") == 40


def test_forward_split_divides_average_price(monkeypatch):
    holder(monkeypatch, quantity=10, price=100.0)
    use_corporate_actions(monkeypatch, alpaca_split("AAPL", 1, 4, TOMORROW.isoformat()))
    run_corporate_actions(TOMORROW)
    assert get_average_buy_price("alice", "AAPL") == Decimal("25")


def test_reverse_split_reduces_shares(monkeypatch):
    holder(monkeypatch, quantity=10)
    use_corporate_actions(monkeypatch, alpaca_split("AAPL", 10, 1, TOMORROW.isoformat()))
    run_corporate_actions(TOMORROW)
    assert get_shares_owned("alice", "AAPL") == 1


def test_reverse_split_can_leave_a_fraction_of_a_share(monkeypatch):
    holder(monkeypatch, quantity=15)
    use_corporate_actions(monkeypatch, alpaca_split("AAPL", 10, 1, TOMORROW.isoformat()))
    run_corporate_actions(TOMORROW)
    assert get_shares_owned("alice", "AAPL") == Decimal("1.5")


def test_split_does_not_change_cash(monkeypatch):
    holder(monkeypatch, quantity=10, price=100.0)
    use_corporate_actions(monkeypatch, alpaca_split("AAPL", 1, 4, TOMORROW.isoformat()))
    run_corporate_actions(TOMORROW)
    assert get_cash_balance("alice") == Decimal("9000.00")


def test_split_is_recorded_in_transaction_history(monkeypatch):
    holder(monkeypatch, quantity=10)
    use_corporate_actions(monkeypatch, alpaca_split("AAPL", 1, 4, TOMORROW.isoformat()))
    run_corporate_actions(TOMORROW)
    assert [split.quantity for split in get_transactions("alice", "SPLIT")] == [30]


def test_split_leaves_other_stocks_alone(monkeypatch):
    holder(monkeypatch, quantity=10, symbol="MSFT")
    use_corporate_actions(monkeypatch, alpaca_split("AAPL", 1, 4, TOMORROW.isoformat()))
    run_corporate_actions(TOMORROW)
    assert get_shares_owned("alice", "MSFT") == 10


# ---------- Exactly once, and only for the right shares ----------

def test_running_twice_applies_a_split_once(monkeypatch):
    holder(monkeypatch, quantity=10)
    use_corporate_actions(monkeypatch, alpaca_split("AAPL", 1, 4, TOMORROW.isoformat()))
    run_corporate_actions(TOMORROW)
    run_corporate_actions(TOMORROW)
    assert get_shares_owned("alice", "AAPL") == 40


def test_split_is_not_applied_before_its_ex_date(monkeypatch):
    holder(monkeypatch, quantity=10)
    use_corporate_actions(monkeypatch, alpaca_split("AAPL", 1, 4, TOMORROW.isoformat()))
    run_corporate_actions(TODAY)
    assert get_shares_owned("alice", "AAPL") == 10


def test_shares_bought_after_the_split_are_not_multiplied(monkeypatch):
    headers = holder_before_today(monkeypatch, quantity=10)
    buy(headers, "AAPL", 5)  # today, at the already-split price
    use_corporate_actions(monkeypatch, alpaca_split("AAPL", 1, 4, TODAY.isoformat()))
    run_corporate_actions(TODAY)
    assert get_shares_owned("alice", "AAPL") == 45


def test_member_who_sold_out_before_the_split_gets_nothing(monkeypatch):
    headers = holder(monkeypatch, quantity=10)
    sell(headers, "AAPL", 10)
    use_corporate_actions(monkeypatch, alpaca_split("AAPL", 1, 4, TOMORROW.isoformat()))
    run_corporate_actions(TOMORROW)
    assert get_shares_owned("alice", "AAPL") == 0


def test_member_who_sold_out_after_the_split_keeps_the_extra_shares(monkeypatch):
    headers = holder_before_today(monkeypatch, quantity=10)
    sell(headers, "AAPL", 10)  # today, before the job ran
    use_corporate_actions(monkeypatch, alpaca_split("AAPL", 1, 4, TODAY.isoformat()))
    run_corporate_actions(TODAY)
    assert get_shares_owned("alice", "AAPL") == 30


def test_reverse_split_never_leaves_negative_shares(monkeypatch):
    headers = holder_before_today(monkeypatch, quantity=10)
    sell(headers, "AAPL", 5)  # today, before the job ran: more than the 1 share they really own after it
    use_corporate_actions(monkeypatch, alpaca_split("AAPL", 10, 1, TODAY.isoformat()))
    run_corporate_actions(TODAY)
    assert get_shares_owned("alice", "AAPL") == 0


def test_second_split_builds_on_the_first(monkeypatch):
    holder(monkeypatch, quantity=10)
    use_corporate_actions(
        monkeypatch,
        alpaca_split("AAPL", 1, 2, TOMORROW.isoformat()),
        alpaca_split("AAPL", 1, 3, (TOMORROW + timedelta(days=1)).isoformat()),
    )
    run_corporate_actions(TOMORROW + timedelta(days=1))
    assert get_shares_owned("alice", "AAPL") == 60


# ---------- What the job asks Alpaca for ----------

def test_first_run_checks_from_the_first_trade(monkeypatch):
    holder(monkeypatch)
    requests_made = use_corporate_actions(monkeypatch)
    run_corporate_actions(TOMORROW)
    assert requests_made[0].start <= TODAY


def test_first_run_uses_the_new_york_date_of_the_first_trade(monkeypatch):
    holder(monkeypatch)
    move_trades_to("alice", datetime(2026, 11, 7, 1, 0))  # 1am UTC on the 7th = 8pm in New York on the 6th
    requests_made = use_corporate_actions(monkeypatch)
    run_corporate_actions(date(2026, 11, 10))
    assert requests_made[0].start == date(2026, 11, 6)


def test_later_runs_recheck_the_last_week(monkeypatch):
    holder(monkeypatch)
    requests_made = use_corporate_actions(monkeypatch)
    run_corporate_actions(TODAY)
    run_corporate_actions(TOMORROW)
    assert requests_made[1].start == TODAY - timedelta(days=corporate_actions.RECHECK_DAYS)


def test_split_published_late_is_still_applied(monkeypatch):
    holder(monkeypatch, quantity=10)
    use_corporate_actions(monkeypatch)  # Alpaca hasn't listed it yet
    run_corporate_actions(TOMORROW)
    use_corporate_actions(monkeypatch, alpaca_split("AAPL", 1, 4, TOMORROW.isoformat()))
    run_corporate_actions(TOMORROW + timedelta(days=1))
    assert get_shares_owned("alice", "AAPL") == 40


def test_no_trades_means_no_alpaca_call():
    # block_real_alpaca fails the test if Alpaca is called
    assert run_corporate_actions(TODAY) == []


# ---------- Running it ----------

def test_report_names_each_split_applied(monkeypatch):
    holder(monkeypatch, quantity=10)
    use_corporate_actions(monkeypatch, alpaca_split("AAPL", 1, 4, TOMORROW.isoformat()))
    assert run_corporate_actions(TOMORROW) == [f"AAPL: split x4 on {TOMORROW}, 1 member(s) adjusted"]


def test_startup_catch_up_survives_an_alpaca_outage(monkeypatch):
    holder(monkeypatch)

    def fail(symbols, start, end):
        raise MarketDataError("Alpaca is down")

    monkeypatch.setattr(corporate_actions, "get_corporate_actions", fail)
    corporate_actions.catch_up_on_startup()  # must not raise