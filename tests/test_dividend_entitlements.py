"""The daily job's dividend handling, step 1: recording what each member is owed on the ex-date."""
from datetime import timedelta
from decimal import Decimal

from helpers import (
    alpaca_dividend,
    alpaca_split,
    buy,
    get_cash_balance,
    get_pending_dividends,
    move_trades_to,
    register_and_login,
    run_corporate_actions,
    sell,
    use_corporate_actions,
    use_market_prices,
)

import corporate_actions
import models
from database import SessionLocal

TODAY = corporate_actions.market_today()
TOMORROW = TODAY + timedelta(days=1)
PAY_DAY = TODAY + timedelta(days=21)


def holder(monkeypatch, quantity=10, price=100.0):
    """A member who bought `quantity` AAPL shares just now (so before any ex-date of tomorrow)."""
    use_market_prices(monkeypatch, {"AAPL": price})
    headers = register_and_login("alice")
    buy(headers, "AAPL", quantity)
    return headers


def holder_before_today(monkeypatch, quantity=10):
    """A member whose shares were bought before today's market day began, so an ex-date of today applies."""
    headers = holder(monkeypatch, quantity)
    move_trades_to("alice", corporate_actions.start_of_market_day(TODAY) - timedelta(hours=1))
    return headers


def dividend(rate=0.25, ex_date=TOMORROW, pay_date=PAY_DAY):
    return alpaca_dividend("AAPL", rate, ex_date.isoformat(), pay_date.isoformat())


# ---------- What gets recorded ----------

def test_holder_is_owed_shares_times_rate(monkeypatch):
    holder(monkeypatch, quantity=10)
    use_corporate_actions(monkeypatch, dividend(rate=0.25))
    run_corporate_actions(TOMORROW)
    assert [owed.amount for owed in get_pending_dividends("alice")] == [Decimal("2.50")]


def test_amount_owed_is_rounded_to_the_cent(monkeypatch):
    holder(monkeypatch, quantity=3)
    use_corporate_actions(monkeypatch, dividend(rate=0.485))  # 3 x 0.485 = 1.455
    run_corporate_actions(TOMORROW)
    assert get_pending_dividends("alice")[0].amount == Decimal("1.46")


def test_fractional_shares_earn_their_share(monkeypatch):
    holder(monkeypatch, quantity=0.5)
    use_corporate_actions(monkeypatch, dividend(rate=0.25))
    run_corporate_actions(TOMORROW)
    assert get_pending_dividends("alice")[0].amount == Decimal("0.13")  # 0.125 rounds up


def test_entitlement_keeps_the_pay_date(monkeypatch):
    holder(monkeypatch)
    use_corporate_actions(monkeypatch, dividend())
    run_corporate_actions(TOMORROW)
    assert get_pending_dividends("alice")[0].payable_date == PAY_DAY


def test_recording_a_dividend_does_not_pay_cash_yet(monkeypatch):
    holder(monkeypatch, quantity=10, price=100.0)
    use_corporate_actions(monkeypatch, dividend())
    run_corporate_actions(TOMORROW)
    assert get_cash_balance("alice") == Decimal("9000.00")


def test_entitlement_starts_unpaid(monkeypatch):
    holder(monkeypatch)
    use_corporate_actions(monkeypatch, dividend())
    run_corporate_actions(TOMORROW)
    assert get_pending_dividends("alice")[0].paid_at is None


def test_report_names_each_dividend(monkeypatch):
    holder(monkeypatch, quantity=10)
    use_corporate_actions(monkeypatch, dividend(rate=0.25))
    assert run_corporate_actions(TOMORROW) == [
        f"AAPL: dividend $0.25/share on {TOMORROW}, 1 member(s) owed $2.50 on {PAY_DAY}"
    ]


# ---------- Who is owed ----------

def test_buying_on_the_ex_date_earns_nothing(monkeypatch):
    holder(monkeypatch)  # bought today
    use_corporate_actions(monkeypatch, dividend(ex_date=TODAY))
    run_corporate_actions(TODAY)
    assert get_pending_dividends("alice") == []


def test_selling_before_the_ex_date_earns_nothing(monkeypatch):
    headers = holder(monkeypatch)
    sell(headers, "AAPL", 10)
    use_corporate_actions(monkeypatch, dividend())
    run_corporate_actions(TOMORROW)
    assert get_pending_dividends("alice") == []


def test_selling_on_the_ex_date_is_still_owed(monkeypatch):
    headers = holder_before_today(monkeypatch, quantity=10)
    sell(headers, "AAPL", 10)  # today: they held the shares going into the ex-date
    use_corporate_actions(monkeypatch, dividend(ex_date=TODAY))
    run_corporate_actions(TODAY)
    assert len(get_pending_dividends("alice")) == 1


def test_dividend_after_a_split_uses_the_new_share_count(monkeypatch):
    holder(monkeypatch, quantity=10)
    day_after = TOMORROW + timedelta(days=1)
    use_corporate_actions(
        monkeypatch,
        alpaca_split("AAPL", 1, 2, TOMORROW.isoformat()),
        dividend(rate=0.25, ex_date=day_after),
    )
    run_corporate_actions(day_after)
    assert get_pending_dividends("alice")[0].shares == 20


# ---------- Exactly once ----------

def test_running_twice_records_a_dividend_once(monkeypatch):
    holder(monkeypatch)
    use_corporate_actions(monkeypatch, dividend())
    run_corporate_actions(TOMORROW)
    run_corporate_actions(TOMORROW)
    assert len(get_pending_dividends("alice")) == 1


def test_dividend_is_not_recorded_before_its_ex_date(monkeypatch):
    holder(monkeypatch)
    use_corporate_actions(monkeypatch, dividend(ex_date=TOMORROW))
    run_corporate_actions(TODAY)
    assert get_pending_dividends("alice") == []


def test_dividends_are_checked_from_the_first_trade_even_if_splits_were_checked_already(monkeypatch):
    # A database from before this change: splits checked through today, dividends never checked
    holder(monkeypatch)
    db = SessionLocal()
    db.add(models.CorporateActionsCheckpoint(kind="split", checked_through=TOMORROW + timedelta(days=30)))
    db.commit()
    db.close()
    requests_made = use_corporate_actions(monkeypatch)
    run_corporate_actions(TOMORROW + timedelta(days=30))
    assert requests_made[0].start <= TODAY