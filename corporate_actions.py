"""Applies stock splits from Alpaca to members' holdings, and handles cash dividends: records what each
member is owed on the ex-date, then pays it into their cash on the pay date.

Run it once a day, before the US market opens:   python -m corporate_actions
It also runs once whenever the server starts. Running it twice, or days late, is safe: each action is
handled exactly once, and only for the shares a member held before its ex-date.
"""
import logging
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import models
from database import SessionLocal, upgrade_database
from market_data import CorporateAction, MarketDataError, get_corporate_actions
from money import round_money, round_shares

logger = logging.getLogger(__name__)

MARKET_TIMEZONE = ZoneInfo("America/New_York")
RECHECK_DAYS = 7  # each run also re-checks the last week, in case Alpaca published an action late
KINDS = ("split", "cash_dividend")  # each kind keeps its own checkpoint, so one added later starts from scratch
SHARE_CHANGES = {"BUY": 1, "SPLIT": 1, "SELL": -1}  # how each transaction type moves a member's share count

def market_today() -> date:
    """Today's date in New York, where the US market's day starts and ends."""
    return datetime.now(MARKET_TIMEZONE).date()


def market_date_of(moment: datetime) -> date:
    """The New York date of a naive UTC timestamp (a trade at 9pm New York is already the next day in UTC)."""
    return moment.replace(tzinfo=timezone.utc).astimezone(MARKET_TIMEZONE).date()


def start_of_market_day(day: date) -> datetime:
    """Midnight New York time on `day`, as naive UTC (the way Transaction timestamps are stored)."""
    return datetime.combine(day, time.min, MARKET_TIMEZONE).astimezone(timezone.utc).replace(tzinfo=None)


def apply_corporate_actions(db, today: date | None = None) -> list[str]:
    """Handles every split and dividend with an ex-date up to `today` not handled yet, then pays every dividend
    due by `today`. Returns one line for each action handled and each dividend paid."""
    today = today or market_today()
    symbols = sorted(symbol for (symbol,) in db.query(models.Transaction.symbol).distinct())
    if not symbols:
        return []  # nobody has ever traded, so no split can affect anyone

    start = min(_check_from(db, kind, today) for kind in KINDS)
    actions = get_corporate_actions(symbols, start, today)  # oldest first, so a split is in place before a later dividend
    already_applied = {action_id for (action_id,) in db.query(models.AppliedCorporateAction.id)}

    report = []
    for action in actions:
        if action.id in already_applied:
            continue
        if action.kind == "split":
            report.append(_apply_split(db, action))
        else:
            report.append(_record_dividend(db, action))
        db.commit()  # each action is saved together with the record that it was handled

    for kind in KINDS:
        _save_checkpoint(db, kind, today)
    db.commit()
    return report + _pay_due_dividends(db, today)


def _check_from(db, kind: str, today: date) -> date:
    """First ex-date to ask Alpaca about: a week before the last check, or the first trade ever made."""
    checkpoint = db.get(models.CorporateActionsCheckpoint, kind)
    if checkpoint:
        return checkpoint.checked_through - timedelta(days=RECHECK_DAYS)
    first_trade = db.query(models.Transaction.timestamp).order_by(models.Transaction.timestamp).first()
    return market_date_of(first_trade[0]) if first_trade else today


def _save_checkpoint(db, kind: str, today: date) -> None:
    checkpoint = db.get(models.CorporateActionsCheckpoint, kind)
    if checkpoint:
        checkpoint.checked_through = today
    else:
        db.add(models.CorporateActionsCheckpoint(kind=kind, checked_through=today))


def _shares_held_before(db, symbol: str, moment: datetime) -> dict[str, Decimal]:
    """{user_id: shares of `symbol` held at `moment`}, replayed from the transaction history."""
    held = defaultdict(Decimal)
    trades = db.query(models.Transaction).filter(
        models.Transaction.symbol == symbol,
        models.Transaction.timestamp < moment,
    )
    for trade in trades:
        # Dividend payments are cash, not shares, so they don't change the count
        held[trade.user_id] += SHARE_CHANGES.get(trade.order_type, 0) * trade.quantity
    return {user_id: shares for user_id, shares in held.items() if shares > 0}


def _apply_split(db, split: CorporateAction) -> str:
    took_effect = start_of_market_day(split.ex_date)
    holders = _shares_held_before(db, split.symbol, took_effect)

    for user_id, shares in holders.items():
        added = round_shares(shares * split.ratio) - shares  # negative for a reverse split
        _adjust_holding(db, user_id, split, shares, added, took_effect)
        db.add(models.Transaction(
            user_id=user_id,
            symbol=split.symbol,
            order_type="SPLIT",
            quantity=added,
            price_per_share=0,
            total_amount=0,
            timestamp=took_effect,  # dated when the split happened, so the history replays in the right order
        ))

    db.add(models.AppliedCorporateAction(
        id=split.id, kind="split", symbol=split.symbol, ex_date=split.ex_date
    ))
    return f"{split.symbol}: split x{float(split.ratio):g} on {split.ex_date}, {len(holders)} member(s) adjusted"


def _record_dividend(db, dividend: CorporateAction) -> str:
    """Records what each member is owed: shares held going into the ex-date x cash per share. Paid later."""
    # The action's record goes in first: each pending dividend points at it
    db.add(models.AppliedCorporateAction(
        id=dividend.id, kind="cash_dividend", symbol=dividend.symbol, ex_date=dividend.ex_date
    ))
    holders = _shares_held_before(db, dividend.symbol, start_of_market_day(dividend.ex_date))
    total = Decimal(0)
    for user_id, shares in holders.items():
        amount = round_money(shares * dividend.cash_per_share)
        total += amount
        db.add(models.PendingDividend(
            action_id=dividend.id,
            user_id=user_id,
            symbol=dividend.symbol,
            shares=shares,
            cash_per_share=dividend.cash_per_share,
            amount=amount,
            ex_date=dividend.ex_date,
            payable_date=dividend.payable_date,
        ))
    return (
        f"{dividend.symbol}: dividend ${dividend.cash_per_share}/share on {dividend.ex_date}, "
        f"{len(holders)} member(s) owed ${total:,.2f} on {dividend.payable_date}"
    )

def _pay_due_dividends(db, today: date) -> list[str]:
    """Moves every unpaid dividend whose pay date has arrived into the member's cash."""
    due = db.query(models.PendingDividend).filter(
        models.PendingDividend.paid_at.is_(None),
        models.PendingDividend.payable_date <= today,
    ).order_by(models.PendingDividend.payable_date, models.PendingDividend.symbol).all()

    paid_by_action = defaultdict(list)
    for owed in due:
        member = db.get(models.User, owed.user_id)
        member.cash_balance += owed.amount
        owed.paid_at = datetime.utcnow()
        db.add(models.Transaction(
            user_id=owed.user_id,
            symbol=owed.symbol,
            order_type="DIVIDEND",
            quantity=owed.shares,              # the shares it was paid on (not a change in shares held)
            price_per_share=owed.cash_per_share,
            total_amount=owed.amount,
        ))
        paid_by_action[(owed.symbol, owed.ex_date)].append(owed.amount)
    db.commit()  # the cash, the "paid" mark and the history entry are saved together

    return [
        f"{symbol}: paid ${sum(amounts):,.2f} dividend (ex {ex_date}) to {len(amounts)} member(s)"
        for (symbol, ex_date), amounts in paid_by_action.items()
    ]

def _adjust_holding(db, user_id, split, shares_before, added, took_effect) -> None:
    holding = db.query(models.Portfolio).filter(
        models.Portfolio.user_id == user_id,
        models.Portfolio.symbol == split.symbol,
    ).first()

    if holding is None:
        # Rare: they sold every share after the split took effect but before this job ran.
        # They still own the extra shares a forward split gave them. Their average price is rebuilt
        # from what they paid before the split (approximate, as the original row is gone).
        if added > 0:
            db.add(models.Portfolio(
                user_id=user_id,
                symbol=split.symbol,
                quantity=added,
                average_buy_price=round_money(_average_paid_before(db, user_id, split.symbol, took_effect) / split.ratio),
            ))
        return

    new_quantity = holding.quantity + added
    if new_quantity <= 0:
        # Rare: a reverse split, and they sold more (unadjusted) shares after it took effect than they now own
        db.delete(holding)
        return
    # Same total cost spread over the new number of shares, so profit/loss is unchanged by the split
    holding.average_buy_price = round_money(holding.quantity * holding.average_buy_price / new_quantity)
    holding.quantity = new_quantity


def _average_paid_before(db, user_id, symbol, moment) -> Decimal:
    buys = db.query(models.Transaction).filter(
        models.Transaction.user_id == user_id,
        models.Transaction.symbol == symbol,
        models.Transaction.order_type == "BUY",
        models.Transaction.timestamp < moment,
    ).all()
    return sum(buy.total_amount for buy in buys) / sum(buy.quantity for buy in buys)


def catch_up_on_startup() -> None:
    """Called when the server starts. Never stops the server from starting, even if Alpaca is down."""
    db = SessionLocal()
    try:
        for line in apply_corporate_actions(db):
            logger.info(line)
    except Exception:
        logger.exception("Could not apply splits and dividends at startup; the server will start anyway")
    finally:
        db.close()


def main() -> None:
    upgrade_database()  # in case the server has never been started on this database
    db = SessionLocal()
    try:
        report = apply_corporate_actions(db)
    except MarketDataError as err:
        raise SystemExit(f"Failed: {err}") from err
    finally:
        db.close()
    print("\n".join(report) if report else "No new splits or dividends, and no dividends due")
    

if __name__ == "__main__":
    main()