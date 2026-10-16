from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

import models
import schemas
from dependencies import get_current_user
from market_data import get_bid_and_ask, get_latest_price, get_tradable_stocks

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


def _match_rank(stock: dict, query: str) -> int | None:
    """How well a stock matches the search text: lower is better, None means no match."""
    symbol, name_words = stock["symbol"], stock["name"].lower().split()
    if symbol == query.upper():
        return 0                                   # exact ticker: "AAPL"
    if symbol.startswith(query.upper()):
        return 1                                   # ticker starts with it: "AA" -> AAPL
    if any(word.startswith(query.lower()) for word in name_words):
        return 2                                   # a word in the name starts with it: "app" -> Apple Inc.
    if query.lower() in stock["name"].lower():
        return 3                                   # anywhere in the name
    return None


@router.get("/search", response_model=list[schemas.StockSearchResult])
def search_stocks(
    q: Annotated[str, Query(min_length=1, max_length=50, examples=["apple"])],
    limit: Annotated[int, Query(ge=1, le=25)] = 10,
    current_user: models.User = Depends(get_current_user)
):
    """Finds stocks by ticker or company name, best matches first, for the trading screen's search box."""
    query = q.strip()
    if not query:
        return []

    matches = []
    for stock in get_tradable_stocks():
        rank = _match_rank(stock, query)
        if rank is not None:
            matches.append((rank, len(stock["symbol"]), stock["symbol"], stock))

    # Best rank first; among equals, shorter tickers first (AAPL before AAPLW), then alphabetical
    matches.sort(key=lambda match: match[:3])
    return [stock for *_, stock in matches[:limit]]