"""Applies stock splits from Alpaca to members' holdings.

Run it once a day, before the US market opens:   python -m corporate_actions
It also runs once whenever the server starts. Running it twice, or days late, is safe: each split is
applied exactly once, and only to the shares a member held before the split took effect.
"""
import logging
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import models
from database import Base, SessionLocal, engine
from market_data import CorporateAction, MarketDataError, get_corporate_actions
from money import round_money, round_shares

logger = logging.getLogger(__name__)

MARKET_TIMEZONE = ZoneInfo("America/New_York")
RECHECK_DAYS = 7  # each run also re-checks the last week, in case Alpaca published an action late


def market_today() -> date:
    """Today's date in New York, where the US market's day starts and ends."""
    return datetime.now(MARKET_TIMEZONE).date()


def start_of_market_day(day: date) -> datetime:
    """Midnight New York time on `day`, as naive UTC (the way Transaction timestamps are stored)."""
    return datetime.combine(day, time.min, MARKET_TIMEZONE).astimezone(timezone.utc).replace(tzinfo=None)


def apply_corporate_actions(db, today: date | None = None) -> list[str]:
    """Applies every split up to `today` that hasn't been applied yet. Returns one line per split applied."""
    today = today or market_today()
    symbols = sorted(symbol for (symbol,) in db.query(models.Transaction.symbol).distinct())
    if not symbols:
        return []  # nobody has ever traded, so no split can affect anyone

    actions = get_corporate_actions(symbols, _check_from(db, today), today)
    already_applied = {action_id for (action_id,) in db.query(models.AppliedCorporateAction.id)}

    report = []
    for action in actions:
        if action.kind == "split" and action.id not in already_applied:
            report.append(_apply_split(db, action))
            db.commit()  # each split is saved together with the record that it was applied

    _save_checkpoint(db, today)
    db.commit()
    return report


def _check_from(db, today: date) -> date:
    """First ex-date to ask Alpaca about: a week before the last check, or the first trade ever made."""
    checkpoint = db.get(models.CorporateActionsCheckpoint, "split")
    if checkpoint:
        return checkpoint.checked_through - timedelta(days=RECHECK_DAYS)
    first_trade = db.query(models.Transaction.timestamp).order_by(models.Transaction.timestamp).first()
    return first_trade[0].date() if first_trade else today


def _save_checkpoint(db, today: date) -> None:
    checkpoint = db.get(models.CorporateActionsCheckpoint, "split")
    if checkpoint:
        checkpoint.checked_through = today
    else:
        db.add(models.CorporateActionsCheckpoint(kind="split", checked_through=today))


def _shares_held_before(db, symbol: str, moment: datetime) -> dict[str, Decimal]:
    """{user_id: shares of `symbol` held at `moment`}, replayed from the transaction history."""
    held = defaultdict(Decimal)
    trades = db.query(models.Transaction).filter(
        models.Transaction.symbol == symbol,
        models.Transaction.timestamp < moment,
    )
    for trade in trades:
        held[trade.user_id] += -trade.quantity if trade.order_type == "SELL" else trade.quantity
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
        logger.exception("Could not apply stock splits at startup; the server will start anyway")
    finally:
        db.close()


def main() -> None:
    Base.metadata.create_all(bind=engine)  # in case the server has never been started on this database
    db = SessionLocal()
    try:
        report = apply_corporate_actions(db)
    except MarketDataError as err:
        raise SystemExit(f"Failed: {err}") from err
    finally:
        db.close()
    print("\n".join(report) if report else "No new splits to apply")


if __name__ == "__main__":
    main()