"""get_corporate_actions(): turning Alpaca's splits and dividends into our own CorporateAction records."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from alpaca.common.exceptions import APIError
from helpers import alpaca_dividend, alpaca_split, use_corporate_actions

import market_data
from market_data import MarketDataError, get_corporate_actions

START, END = date(2026, 11, 1), date(2026, 11, 30)


def fetch_one(monkeypatch, action):
    use_corporate_actions(monkeypatch, action)
    [result] = get_corporate_actions(["AAPL"], START, END)
    return result


def test_forward_split_is_a_split(monkeypatch):
    action = fetch_one(monkeypatch, alpaca_split("AAPL", 1, 4, "2026-11-10"))
    assert action.kind == "split"


def test_forward_split_ratio_is_new_shares_per_old_share(monkeypatch):
    action = fetch_one(monkeypatch, alpaca_split("AAPL", 1, 4, "2026-11-10"))
    assert action.ratio == Decimal("4")


def test_reverse_split_ratio_is_below_one(monkeypatch):
    action = fetch_one(monkeypatch, alpaca_split("AAPL", 10, 1, "2026-11-10"))
    assert action.ratio == Decimal("0.1")


def test_uneven_split_ratio_is_exact(monkeypatch):
    action = fetch_one(monkeypatch, alpaca_split("AAPL", 2, 3, "2026-11-10"))
    assert action.ratio == Decimal("1.5")


def test_cash_dividend_is_a_cash_dividend(monkeypatch):
    action = fetch_one(monkeypatch, alpaca_dividend("AAPL", 0.26, "2026-11-10", "2026-11-13"))
    assert action.kind == "cash_dividend"


def test_cash_dividend_amount_is_exact(monkeypatch):
    action = fetch_one(monkeypatch, alpaca_dividend("AAPL", 0.26, "2026-11-10", "2026-11-13"))
    assert action.cash_per_share == Decimal("0.26")


def test_cash_dividend_keeps_its_pay_date(monkeypatch):
    action = fetch_one(monkeypatch, alpaca_dividend("AAPL", 0.26, "2026-11-10", "2026-11-13"))
    assert action.payable_date == date(2026, 11, 13)


def test_missing_pay_date_falls_back_to_ex_date(monkeypatch):
    action = fetch_one(monkeypatch, alpaca_dividend("AAPL", 0.26, "2026-11-10"))
    assert action.payable_date == date(2026, 11, 10)


def test_ex_date_is_a_date(monkeypatch):
    action = fetch_one(monkeypatch, alpaca_split("AAPL", 1, 4, "2026-11-10"))
    assert action.ex_date == date(2026, 11, 10)


def test_alpaca_id_is_kept(monkeypatch):
    action = fetch_one(monkeypatch, alpaca_split("AAPL", 1, 4, "2026-11-10", action_id="abc-123"))
    assert action.id == "abc-123"


def test_other_kinds_of_action_are_ignored(monkeypatch):
    spin_off = ("spin_offs", {"id": "x", "source_symbol": "AAPL", "ex_date": "2026-11-10"})
    use_corporate_actions(monkeypatch, spin_off)
    assert get_corporate_actions(["AAPL"], START, END) == []


def test_actions_are_returned_oldest_first(monkeypatch):
    use_corporate_actions(
        monkeypatch,
        alpaca_dividend("AAPL", 0.26, "2026-11-20"),
        alpaca_split("AAPL", 1, 4, "2026-11-05"),
    )
    actions = get_corporate_actions(["AAPL"], START, END)
    assert [action.ex_date for action in actions] == [date(2026, 11, 5), date(2026, 11, 20)]


def test_asks_alpaca_for_the_given_symbols(monkeypatch):
    requests_made = use_corporate_actions(monkeypatch)
    get_corporate_actions(["AAPL", "MSFT"], START, END)
    assert requests_made[0].symbols == ["AAPL", "MSFT"]


def test_asks_alpaca_from_the_start_date(monkeypatch):
    requests_made = use_corporate_actions(monkeypatch)
    get_corporate_actions(["AAPL"], START, END)
    assert requests_made[0].start == START


def test_asks_alpaca_past_the_end_date_to_catch_late_pay_dates(monkeypatch):
    # Alpaca filters by process date (a dividend's pay date), not ex-date
    requests_made = use_corporate_actions(monkeypatch)
    get_corporate_actions(["AAPL"], START, END)
    assert requests_made[0].end == END + timedelta(days=market_data.CORPORATE_ACTIONS_LOOKAHEAD_DAYS)


def test_dividend_paid_after_end_is_returned_when_ex_date_is_in_range(monkeypatch):
    use_corporate_actions(monkeypatch, alpaca_dividend("KO", 0.485, "2026-11-28", "2026-12-15"))
    assert len(get_corporate_actions(["KO"], START, END)) == 1


def test_action_with_ex_date_after_end_is_left_out(monkeypatch):
    use_corporate_actions(monkeypatch, alpaca_dividend("KO", 0.485, "2026-12-01", "2026-12-15"))
    assert get_corporate_actions(["KO"], START, END) == []


def test_action_with_ex_date_before_start_is_left_out(monkeypatch):
    # Paid inside the window (so Alpaca returns it) but went ex-dividend before it
    use_corporate_actions(monkeypatch, alpaca_dividend("KO", 0.485, "2026-10-30", "2026-11-14"))
    assert get_corporate_actions(["KO"], START, END) == []


def test_no_symbols_means_no_alpaca_call():
    # block_real_alpaca fails the test if Alpaca is called
    assert get_corporate_actions([], START, END) == []


def test_alpaca_error_raises_market_data_error(monkeypatch):
    def fail(request):
        raise APIError("service unavailable")

    monkeypatch.setattr(market_data.corporate_actions_client, "get_corporate_actions", fail)
    with pytest.raises(MarketDataError):
        get_corporate_actions(["AAPL"], START, END)