import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import relationship

from config import STARTING_CASH
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    cash_balance = Column(Numeric(14, 2), default=STARTING_CASH)  # exact to the cent. Default starting paper capital ($10,000)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    portfolios = relationship("Portfolio", back_populates="owner", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, nullable=False, index=True)  # e.g., "AAPL"
    quantity = Column(Numeric(18, 6), nullable=False, default=0)  # up to 6 decimal places of a share
    average_buy_price = Column(Numeric(18, 2), nullable=False)
    
    # Relationship back to User
    owner = relationship("User", back_populates="portfolios")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, nullable=False)
    order_type = Column(String, nullable=False)  # "BUY" or "SELL"
    quantity = Column(Numeric(18, 6), nullable=False)
    price_per_share = Column(Numeric(14, 4), nullable=False)
    total_amount = Column(Numeric(14, 2), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationship back to User
    user = relationship("User", back_populates="transactions")

