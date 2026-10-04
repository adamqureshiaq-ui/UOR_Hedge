from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from dependencies import get_current_user
from market_data import get_latest_price

router = APIRouter(prefix="/trade", tags=["Trading"])


@router.post("/buy", response_model=schemas.TradeResponse)
def buy_stock(
    trade_data: schemas.TradeRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Executes a virtual market buy order using real-time stock prices."""
    symbol = trade_data.symbol.upper()
    qty = trade_data.quantity

    # 1. Fetch live stock price from Alpaca (raises a 400 if the symbol can't be priced)
    price_per_share = get_latest_price(symbol)
    total_cost = price_per_share * qty

    # 2. Check if user has sufficient cash
    if current_user.cash_balance < total_cost:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient funds. Required: ${total_cost:,.2f}, Available: ${current_user.cash_balance:,.2f}"
        )

    # 3. Deduct cash balance
    current_user.cash_balance -= total_cost

    # 4. Update or Create Portfolio entry
    portfolio_item = db.query(models.Portfolio).filter(
        models.Portfolio.user_id == current_user.id,
        models.Portfolio.symbol == symbol
    ).first()

    if portfolio_item:
        # Calculate new weighted average buy price
        total_existing_cost = portfolio_item.quantity * portfolio_item.average_buy_price
        new_total_qty = portfolio_item.quantity + qty
        portfolio_item.average_buy_price = (total_existing_cost + total_cost) / new_total_qty
        portfolio_item.quantity = new_total_qty
    else:
        portfolio_item = models.Portfolio(
            user_id=current_user.id,
            symbol=symbol,
            quantity=qty,
            average_buy_price=price_per_share
        )
        db.add(portfolio_item)

    # 5. Log Transaction
    transaction_record = models.Transaction(
        user_id=current_user.id,
        symbol=symbol,
        order_type="BUY",
        quantity=qty,
        price_per_share=price_per_share,
        total_amount=total_cost
    )
    db.add(transaction_record)

    db.commit()

    return {
        "message": f"Successfully purchased {qty} shares of {symbol}",
        "symbol": symbol,
        "quantity": qty,
        "price_per_share": round(price_per_share, 2),
        "total_cost": round(total_cost, 2),
        "remaining_cash": round(current_user.cash_balance, 2)
    }


# POST /trade/sell goes here (feature/trade-sell)