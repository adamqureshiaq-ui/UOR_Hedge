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
    quantity: float = Field(..., gt=0, example=5.0)

class TradeResponse(BaseModel):
    message: str
    symbol: str
    quantity: float
    price_per_share: float
    total_cost: float
    remaining_cash: float