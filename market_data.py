"""Everything that talks to Alpaca lives here."""
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from alpaca.common.exceptions import APIError
from alpaca.data.enums import Adjustment, CorporateActionsType
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.historical.corporate_actions import CorporateActionsClient
from alpaca.data.requests import (
    CorporateActionsRequest,
    StockBarsRequest,
    StockLatestQuoteRequest,
    StockLatestTradeRequest,
)
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import AssetClass, AssetStatus
from alpaca.trading.requests import GetAssetsRequest
from fastapi import HTTPException, status

from config import ALPACA_API_KEY, ALPACA_SECRET_KEY
from money import to_decimal

if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
    raise ValueError(
        "Alpaca API keys missing! Ensure your .env contains ALPACA_API_KEY and ALPACA_SECRET_KEY."
    )

stock_data_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)
# Only used to list stocks. raw_data=True returns Alpaca's plain JSON (dicts) instead of alpaca-py models,
# so a new exchange the library doesn't know yet (e.g. TXSE) can't make the whole list fail to load.
trading_client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True, raw_data=True)

# Splits and dividends. raw_data=True for the same reason, and because alpaca-py's models drop each action's id
corporate_actions_client = CorporateActionsClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, raw_data=True)

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
    if not symbols:
        return {}
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


def get_daily_closes(symbols: list[str], lookback_days: int = 365) -> dict[str, list[float]]:
    """Daily closing prices (oldest first) for each symbol, using ONE Alpaca request.

    Only trading days that every symbol has a bar for are kept, so the lists line up day by day.
    """
    if not symbols:
        return {}
    now = datetime.now(timezone.utc)
    try:
        request_params = StockBarsRequest(
            symbol_or_symbols=symbols,
            timeframe=TimeFrame.Day,
            start=now - timedelta(days=lookback_days),
            end=now - timedelta(minutes=15),   # free plans can't query the most recent 15 minutes
            adjustment=Adjustment.ALL,         # adjust for splits/dividends so they don't look like crashes
        )
        bars = stock_data_client.get_stock_bars(request_params)
        closes_by_date = {
            symbol: {bar.timestamp.date(): float(bar.close) for bar in bars[symbol]}
            for symbol in symbols
        }
    except (APIError, KeyError) as err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not fetch historical prices from the market data provider. Try again shortly."
        ) from err

    shared_dates = sorted(set.intersection(*(set(dates) for dates in closes_by_date.values())))
    return {symbol: [closes_by_date[symbol][date] for date in shared_dates] for symbol in symbols}


def get_bid_and_ask(symbol: str) -> tuple[float | None, float | None]:
    """Current bid and ask for one symbol. A side is None when nobody is bidding/asking (e.g. market closed)."""
    quote = _get_latest_quote(symbol)
    bid, ask = float(quote.bid_price), float(quote.ask_price)
    return (bid if bid > 0 else None, ask if ask > 0 else None)


# ---------- Stock list (for search) ----------

STOCK_LIST_MAX_AGE_SECONDS = 24 * 60 * 60   # the list of listed companies barely changes within a day
_stock_list_cache = {"stocks": [], "loaded_at": None}


def get_tradable_stocks() -> list[dict]:
    """Every active, tradable US stock as {"symbol", "name", "exchange"}.

    Alpaca returns about 10,000 of them, so the list is downloaded once and kept in memory for a day.
    """
    loaded_at = _stock_list_cache["loaded_at"]
    if loaded_at is not None and time.monotonic() - loaded_at < STOCK_LIST_MAX_AGE_SECONDS:
        return _stock_list_cache["stocks"]

    try:
        assets = trading_client.get_all_assets(
            GetAssetsRequest(status=AssetStatus.ACTIVE, asset_class=AssetClass.US_EQUITY)
        )
    except APIError as err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not fetch the list of stocks from the market data provider. Try again shortly."
        ) from err

    _stock_list_cache["stocks"] = [
        {"symbol": asset["symbol"], "name": asset.get("name") or "", "exchange": asset.get("exchange") or ""}
        for asset in assets
        if asset.get("tradable")
    ]
    _stock_list_cache["loaded_at"] = time.monotonic()
    return _stock_list_cache["stocks"]


def clear_stock_list_cache() -> None:
    """Forget the cached stock list (used by tests so each one starts fresh)."""
    _stock_list_cache["stocks"] = []
    _stock_list_cache["loaded_at"] = None


# ---------- Corporate actions (splits and dividends) ----------

# Alpaca filters corporate actions by process date, which for a cash dividend is its pay date (often weeks
# after the ex-date). To catch every action whose ex-date is in range, ask for this many days past the end.
CORPORATE_ACTIONS_LOOKAHEAD_DAYS = 90


class MarketDataError(RuntimeError):
    """Alpaca couldn't answer. Raised outside web requests, where an HTTPException would mean nothing."""


@dataclass(frozen=True)
class CorporateAction:
    """A split or cash dividend, in our own shape so the rest of the app never sees Alpaca's format."""
    id: str                               # Alpaca's id: lets us apply each action exactly once
    kind: str                             # "split" or "cash_dividend"
    symbol: str
    ex_date: date                         # first day the stock trades at the new price / without the dividend
    payable_date: date                    # day dividend cash is paid (the ex-date if Alpaca doesn't give one)
    ratio: Decimal | None = None          # splits: new shares per old share (4 for 4-for-1, 0.1 for 1-for-10)
    cash_per_share: Decimal | None = None # cash dividends: dollars paid per share held


def get_corporate_actions(symbols: list[str], start: date, end: date) -> list[CorporateAction]:
    """Every split and cash dividend for these symbols with an ex-date from start to end (inclusive), oldest first.

    Other kinds of action (mergers, spin-offs, symbol changes...) are left out on purpose.
    """
    if not symbols:
        return []
    try:
        raw = corporate_actions_client.get_corporate_actions(
            CorporateActionsRequest(
                symbols=symbols,
                types=[
                    CorporateActionsType.FORWARD_SPLIT,
                    CorporateActionsType.REVERSE_SPLIT,
                    CorporateActionsType.CASH_DIVIDEND,
                ],
                start=start,
                end=end + timedelta(days=CORPORATE_ACTIONS_LOOKAHEAD_DAYS),
                limit=None,  # no cap: follow every page Alpaca returns
            )
        )
    except APIError as err:
        raise MarketDataError("Could not fetch splits and dividends from Alpaca.") from err

    actions = []
    for item in raw.get("forward_splits", []) + raw.get("reverse_splits", []):
        actions.append(_to_corporate_action(
            item, "split", ratio=to_decimal(item["new_rate"]) / to_decimal(item["old_rate"])
        ))
    for item in raw.get("cash_dividends", []):
        actions.append(_to_corporate_action(item, "cash_dividend", cash_per_share=to_decimal(item["rate"])))
    in_range = [action for action in actions if start <= action.ex_date <= end]
    return sorted(in_range, key=lambda action: (action.ex_date, action.symbol))

def _to_corporate_action(item: dict, kind: str, **amount) -> CorporateAction:
    ex_date = date.fromisoformat(item["ex_date"])
    payable_date = item.get("payable_date")
    return CorporateAction(
        id=item["id"],
        kind=kind,
        symbol=item["symbol"],
        ex_date=ex_date,
        payable_date=date.fromisoformat(payable_date) if payable_date else ex_date,
        **amount,
    )