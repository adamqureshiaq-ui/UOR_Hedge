from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from dependencies import get_current_user
from market_data import get_latest_prices

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])


@router.get("", response_model=schemas.PortfolioResponse)
def get_portfolio(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Values the member's holdings at live market prices and returns their total equity."""
    # 1. Pull the user's holdings from the database
    holdings = db.query(models.Portfolio).filter(
        models.Portfolio.user_id == current_user.id
    ).order_by(models.Portfolio.symbol).all()

    # 2. Fetch live prices for every symbol in ONE Alpaca request (skip Alpaca if they own nothing)
    symbols = [holding.symbol for holding in holdings]
    prices = get_latest_prices(symbols) if symbols else {}

    # 3. Value each holding
    holding_rows = []
    holdings_value = 0.0
    for holding in holdings:
        current_price = prices[holding.symbol]
        market_value = holding.quantity * current_price
        cost_basis = holding.quantity * holding.average_buy_price
        holdings_value += market_value
        holding_rows.append({
            "symbol": holding.symbol,
            "quantity": holding.quantity,
            "average_buy_price": round(holding.average_buy_price, 2),
            "current_price": round(current_price, 2),
            "market_value": round(market_value, 2),
            "unrealized_profit_loss": round(market_value - cost_basis, 2),
        })

    # 4. Total equity = cash + current value of all holdings
    return {
        "cash_balance": round(current_user.cash_balance, 2),
        "holdings_value": round(holdings_value, 2),
        "total_equity": round(current_user.cash_balance + holdings_value, 2),
        "holdings": holding_rows,
    }