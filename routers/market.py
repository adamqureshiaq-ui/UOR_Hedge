from typing import Annotated

from fastapi import APIRouter, Depends, Path

import models
import schemas
from dependencies import get_current_user
from market_data import get_bid_and_ask, get_latest_price

router = APIRouter(prefix="/market", tags=["Market Data"])


@router.get("/quote/{symbol}", response_model=schemas.QuoteResponse)
def get_quote(
    symbol: Annotated[str, Path(pattern=r"^[A-Za-z.]{1,10}$", examples=["AAPL"])],
    current_user: models.User = Depends(get_current_user)
):
    """Live prices for one stock, so a member can see what they'd pay or receive before trading."""
    symbol = symbol.upper()
    last_trade_price = get_latest_price(symbol)
    bid_price, ask_price = get_bid_and_ask(symbol)

    return {
        "symbol": symbol,
        "last_trade_price": round(last_trade_price, 2),
        "bid_price": round(bid_price, 2) if bid_price is not None else None,
        "ask_price": round(ask_price, 2) if ask_price is not None else None,
        "spread": round(ask_price - bid_price, 2) if bid_price is not None and ask_price is not None else None,
    }