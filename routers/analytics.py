import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from dependencies import get_current_user
from market_data import get_daily_closes, get_latest_prices
from simulations import PERCENTILES, estimate_gbm_parameters, simulate_portfolio_values

router = APIRouter(prefix="/analytics", tags=["Analytics"])

MIN_HISTORY_DAYS = 30

ASSUMPTIONS = (
    "Geometric Brownian motion fitted to about one year of daily prices. Assumes future returns, volatility "
    "and correlations look like the past year's, that returns follow a bell curve (real markets have more "
    "extreme days), and that you make no trades. This shows a range of possible outcomes, not a forecast."
)


@router.post("/monte-carlo", response_model=schemas.MonteCarloResponse)
def run_monte_carlo(
    request: schemas.MonteCarloRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Simulates thousands of possible futures for the member's portfolio using geometric Brownian motion."""
    # 1. The user's holdings
    holdings = db.query(models.Portfolio).filter(
        models.Portfolio.user_id == current_user.id
    ).order_by(models.Portfolio.symbol).all()
    if not holdings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have no holdings to simulate. Buy some shares first."
        )
    symbols = [holding.symbol for holding in holdings]

    # 2. Today's value of each position (same live prices as /portfolio)
    prices = get_latest_prices(symbols)
    position_values = np.array([float(holding.quantity) * prices[holding.symbol] for holding in holdings])
    cash = float(current_user.cash_balance)  # numpy works in floats
    starting_value = cash + position_values.sum()

    # 3. About a year of daily closes, one Alpaca request for all symbols
    closes_by_symbol = get_daily_closes(symbols)
    closes = np.column_stack([closes_by_symbol[symbol] for symbol in symbols])
    if len(closes) < MIN_HISTORY_DAYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not enough shared price history to simulate (need {MIN_HISTORY_DAYS} trading days, found {len(closes)})."
        )

    # 4. Fit GBM to the history and simulate
    mean_log_returns, covariance = estimate_gbm_parameters(closes)
    values_by_day = simulate_portfolio_values(
        position_values, cash, mean_log_returns, covariance,
        days=request.days, simulations=request.simulations, seed=request.seed,
    )

    # 5. Summarise the results
    final_values = values_by_day[-1]
    p5, p25, p50, p75, p95 = np.percentile(final_values, PERCENTILES)
    daily_bands = np.percentile(values_by_day, (5, 50, 95), axis=1)

    return {
        "method": "gbm",
        "days": request.days,
        "simulations": request.simulations,
        "historical_days_used": len(closes) - 1,
        "starting_value": round(starting_value, 2),
        "expected_value": round(final_values.mean(), 2),
        "final_value_percentiles": {
            "p5": round(p5, 2), "p25": round(p25, 2), "p50": round(p50, 2),
            "p75": round(p75, 2), "p95": round(p95, 2),
        },
        "probability_of_loss": round(float((final_values < starting_value).mean()) * 100, 2),
        "value_at_risk_95": round(max(starting_value - p5, 0.0), 2),
        "projection": [
            {"day": day + 1, "p5": round(low, 2), "p50": round(mid, 2), "p95": round(high, 2)}
            for day, (low, mid, high) in enumerate(daily_bands.T)
        ],
        "assumptions": ASSUMPTIONS,
    }