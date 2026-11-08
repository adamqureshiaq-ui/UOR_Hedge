"""The single definition of how a member's wealth is valued, shared by /portfolio and /leaderboard."""
from sqlalchemy import func

import models


def calculate_holdings_value(holdings, prices: dict[str, float]) -> float:
    """Current market value of a list of Portfolio rows, given {symbol: price}.

    An estimate for display and ranking (live prices are floats), so float maths is fine here.
    """
    return sum(float(holding.quantity) * prices[holding.symbol] for holding in holdings)


def pending_dividend_totals(db, user_id: str | None = None) -> dict[str, float]:
    """{user_id: dividends owed but not yet paid}. Counted in equity: the share price already dropped on the
    ex-date, so leaving this out would make dividend holders look poorer until the cash arrives."""
    query = db.query(models.PendingDividend.user_id, func.sum(models.PendingDividend.amount)).filter(
        models.PendingDividend.paid_at.is_(None)
    )
    if user_id is not None:
        query = query.filter(models.PendingDividend.user_id == user_id)
    return {owner: float(total) for owner, total in query.group_by(models.PendingDividend.user_id)}