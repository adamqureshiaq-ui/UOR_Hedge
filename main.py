import os
from pathlib import Path

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestTradeRequest

# Alpaca SDK Imports
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

import auth
import models
import schemas

# Local App Imports
from database import Base, engine, get_db

# 1. Load Environment Variables
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

if not API_KEY or not SECRET_KEY:
    raise ValueError(
        f"Alpaca API keys missing! Looking in: {env_path}\n"
        "Ensure your .env contains ALPACA_API_KEY and ALPACA_SECRET_KEY."
    )

# 2. Initialize Database Tables
Base.metadata.create_all(bind=engine)

# 3. Initialize FastAPI and Alpaca Clients
app = FastAPI(title="Finance Society Broker API")
trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)
stock_data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)

# 4. OAuth2 Authentication Security Scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    """Dependency that decodes the JWT token and verifies the logged-in user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = auth.decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user


# ==========================================
# PUBLIC & SYSTEM ROUTES
# ==========================================

@app.get("/")
def home():
    return {"status": "Backend, Database, and Trading Engines are operational!"}

@app.get("/account")
def get_account_status():
    """Fetches master Alpaca paper trading account status and balances."""
    account = trading_client.get_account()
    return {
        "status": account.status,
        "buying_power": account.buying_power,
        "cash": account.cash
    }

@app.post("/test-trade")
def execute_test_trade():
    """Submits a test market buy order for 1 paper share of AAPL directly via Alpaca."""
    order_data = MarketOrderRequest(
        symbol="AAPL",
        qty=1,
        side=OrderSide.BUY,
        time_in_force=TimeInForce.DAY
    )
    order = trading_client.submit_order(order_data=order_data)
    return {
        "message": "Order submitted successfully!",
        "order_id": str(order.id),
        "symbol": order.symbol,
        "qty": float(order.qty),
        "status": str(order.status)
    }


# ==========================================
# AUTHENTICATION ROUTES
# ==========================================

@app.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    """Registers a new society member with $10,000 starting cash."""
    existing_username = db.query(models.User).filter(models.User.username == user_data.username).first()
    if existing_username:
        raise HTTPException(status_code=400, detail="Username already taken.")

    existing_email = db.query(models.User).filter(models.User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered.")

    new_user = models.User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=auth.hash_password(user_data.password)
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login", response_model=schemas.Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    """Logs in a member and issues a JWT Bearer token."""
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth.create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/me", response_model=schemas.UserResponse)
def get_user_profile(current_user: models.User = Depends(get_current_user)):
    """Protected route: Returns profile info for the currently authenticated member."""
    return current_user


# ==========================================
# VIRTUAL TRADING ROUTES
# ==========================================

@app.post("/trade/buy", response_model=schemas.TradeResponse)
def buy_stock(
    trade_data: schemas.TradeRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Executes a virtual market buy order using real-time stock prices."""
    symbol = trade_data.symbol.upper()
    qty = trade_data.quantity

    # 1. Fetch live stock price from Alpaca
    try:
        request_params = StockLatestTradeRequest(symbol_or_symbols=symbol)
        latest_trade = stock_data_client.get_stock_latest_trade(request_params)
        price_per_share = float(latest_trade[symbol].price)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch market price for '{symbol}'. Verify ticker symbol."
        )

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
