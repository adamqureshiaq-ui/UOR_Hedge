from collections import defaultdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

import models
import schemas
from config import STARTING_CASH
from database import get_db
from dependencies import get_current_user
from market_data import get_latest_prices
from valuation import calculate_holdings_value

router = APIRouter(prefix="/leaderboard", tags=["Society"])


@router.get("", response_model=schemas.LeaderboardResponse)
def get_leaderboard(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Ranks every member by real-time total equity (cash + live value of their holdings)."""
    # 1. Load every member and every holding in two queries (not one query per member)
    users = db.query(models.User).all()
    all_holdings = db.query(models.Portfolio).all()

    holdings_by_user = defaultdict(list)
    for holding in all_holdings:
        holdings_by_user[holding.user_id].append(holding)

    # 2. One Alpaca request for every distinct symbol anyone owns
    prices = get_latest_prices(sorted({holding.symbol for holding in all_holdings}))

    # 3. Work out each member's equity, then sort: highest equity first, username breaks ties
    standings = []
    for user in users:
        equity = user.cash_balance + calculate_holdings_value(holdings_by_user[user.id], prices)
        standings.append((user.username, round(equity, 2)))
    standings.sort(key=lambda standing: (-standing[1], standing[0]))

    # 4. Assign ranks; members with exactly the same equity share a rank (1, 2, 2, 4)
    entries = []
    for position, (username, equity) in enumerate(standings, start=1):
        tied_with_previous = entries and entries[-1]["total_equity"] == equity
        entries.append({
            "rank": entries[-1]["rank"] if tied_with_previous else position,
            "username": username,
            "total_equity": equity,
            "return_percent": round((equity - STARTING_CASH) / STARTING_CASH * 100, 2),
        })

    my_rank = next(entry["rank"] for entry in entries if entry["username"] == current_user.username)
    return {"my_rank": my_rank, "total_members": len(entries), "entries": entries[:limit]}