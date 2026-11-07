import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
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
    order_type = Column(String, nullable=False)  # "BUY", "SELL" or "SPLIT" (quantity = shares added, negative for a reverse split)
    quantity = Column(Numeric(18, 6), nullable=False)  # up to 6 decimal places of a share
    price_per_share = Column(Numeric(14, 4), nullable=False)
    total_amount = Column(Numeric(14, 2), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationship back to User
    user = relationship("User", back_populates="transactions")


class AppliedCorporateAction(Base):
    """A split or dividend that has been applied. Alpaca's id as the key means it can't be applied twice."""
    __tablename__ = "applied_corporate_actions"

    id = Column(String, primary_key=True)  # Alpaca's id for the action
    kind = Column(String, nullable=False)  # "split" or "cash_dividend"
    symbol = Column(String, nullable=False)
    ex_date = Column(Date, nullable=False)
    applied_at = Column(DateTime, default=datetime.utcnow)


class CorporateActionsCheckpoint(Base):
    """The last market day the corporate-actions job has checked, one row per kind of action."""
    __tablename__ = "corporate_actions_checkpoints"

    kind = Column(String, primary_key=True)  # "split" or "cash_dividend"
    checked_through = Column(Date, nullable=False)


class PendingDividend(Base):
    """Cash a member is owed for shares they held going into a dividend's ex-date. Paid on payable_date."""
    __tablename__ = "pending_dividends"
    __table_args__ = (UniqueConstraint("action_id", "user_id"),)  # one entitlement per member per dividend

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    action_id = Column(String, ForeignKey("applied_corporate_actions.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, nullable=False)
    shares = Column(Numeric(18, 6), nullable=False)        # shares held at the end of the day before the ex-date
    cash_per_share = Column(Numeric(14, 6), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)        # shares x cash_per_share, to the cent
    ex_date = Column(Date, nullable=False)
    payable_date = Column(Date, nullable=False)
    paid_at = Column(DateTime, nullable=True)              # set when the cash is paid (next PR)