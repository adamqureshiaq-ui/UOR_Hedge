"""Everything that talks to Alpaca lives here."""
from alpaca.common.exceptions import APIError
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestTradeRequest, StockLatestQuoteRequest
from fastapi import HTTPException, status

from config import ALPACA_API_KEY, ALPACA_SECRET_KEY

if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
    raise ValueError(
        "Alpaca API keys missing! Ensure your .env contains ALPACA_API_KEY and ALPACA_SECRET_KEY."
    )

stock_data_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)


def get_latest_price(symbol: str) -> float:
    """Returns the last traded price for one symbol, or raises a 400 if Alpaca can't price it."""
    try:
        request_params = StockLatestTradeRequest(symbol_or_symbols=symbol)
        latest_trade = stock_data_client.get_stock_latest_trade(request_params)
        return float(latest_trade[symbol].price)
    except (APIError, KeyError) as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch market price for '{symbol}'. Verify ticker symbol."
        ) from err


def get_latest_prices(symbols: list[str]) -> dict[str, float]:
    """Returns {symbol: last traded price} for many symbols using ONE Alpaca request."""
    try:
        request_params = StockLatestTradeRequest(symbol_or_symbols=symbols)
        latest_trades = stock_data_client.get_stock_latest_trade(request_params)
        return {symbol: float(latest_trades[symbol].price) for symbol in symbols}
    except (APIError, KeyError) as err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not fetch live prices from the market data provider. Try again shortly."
        ) from err

    

def _get_latest_quote(symbol: str):
    """Fetches the current quote (bid and ask) for one symbol, or raises a 400 if Alpaca can't quote it."""
    try:
        request_params = StockLatestQuoteRequest(symbol_or_symbols=symbol)
        return stock_data_client.get_stock_latest_quote(request_params)[symbol]
    except (APIError, KeyError) as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch a live quote for '{symbol}'. Verify ticker symbol."
        ) from err


def _require_live_price(price: float, side: str, symbol: str) -> float:
    """Rejects a missing quote side (Alpaca reports 0 when nobody is bidding/asking, e.g. outside market hours)."""
    if price <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No live {side} price for '{symbol}' right now. The market may be closed; try again during trading hours."
        )
    return price


def get_latest_bid_price(symbol: str) -> float:
    """Highest price a buyer is offering right now: what a market SELL order would receive."""
    return _require_live_price(float(_get_latest_quote(symbol).bid_price), "bid", symbol)


def get_latest_ask_price(symbol: str) -> float:
    """Lowest price a seller is accepting right now: what a market BUY order would pay."""
    return _require_live_price(float(_get_latest_quote(symbol).ask_price), "ask", symbol)