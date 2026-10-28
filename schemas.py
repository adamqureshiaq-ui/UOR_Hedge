from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    cash_balance: float

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: str | None = None

class TradeRequest(BaseModel):
    symbol: str = Field(..., example="AAPL")
    quantity: Decimal = Field(..., gt=0, decimal_places=6, example=5)  # exact; at most 6 decimal places

class TradeResponse(BaseModel):
    message: str
    symbol: str
    quantity: float
    price_per_share: float
    total_cost: float
    remaining_cash: float

class HoldingResponse(BaseModel):
    symbol: str
    quantity: float
    average_buy_price: float
    current_price: float
    market_value: float
    unrealized_profit_loss: float

class PortfolioResponse(BaseModel):
    cash_balance: float
    holdings_value: float
    total_equity: float
    holdings: list[HoldingResponse]

class LeaderboardEntry(BaseModel):
    rank: int
    username: str
    total_equity: float
    return_percent: float


class LeaderboardResponse(BaseModel):
    my_rank: int
    total_members: int
    entries: list[LeaderboardEntry]


class MonteCarloRequest(BaseModel):
    days: int = Field(21, ge=1, le=252, description="Trading days to simulate (21 ≈ 1 month, 252 ≈ 1 year)")
    simulations: int = Field(1000, ge=100, le=10000, description="Number of possible futures to generate")
    seed: int | None = Field(None, description="Set this to get the same results every time")


class ValuePercentiles(BaseModel):
    p5: float
    p25: float
    p50: float
    p75: float
    p95: float


class ProjectionPoint(BaseModel):
    day: int
    p5: float
    p50: float
    p95: float


class MonteCarloResponse(BaseModel):
    method: str
    days: int
    simulations: int
    historical_days_used: int
    starting_value: float
    expected_value: float
    final_value_percentiles: ValuePercentiles
    probability_of_loss: float
    value_at_risk_95: float
    projection: list[ProjectionPoint]
    assumptions: str


class QuoteResponse(BaseModel):
    symbol: str
    last_trade_price: float
    bid_price: float | None   # what you'd get if you sold now (None = no live bid, e.g. market closed)
    ask_price: float | None   # what you'd pay if you bought now (None = no live ask)
    spread: float | None      # ask − bid: the hidden cost of buying and immediately selling


class StockSearchResult(BaseModel):
    symbol: str
    name: str
    exchange: str