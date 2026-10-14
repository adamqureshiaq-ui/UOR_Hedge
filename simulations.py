"""Monte Carlo simulation of a portfolio using geometric Brownian motion (GBM).

Pure maths, no FastAPI or Alpaca, so it can be tested on its own.
"""
import numpy as np

PERCENTILES = (5, 25, 50, 75, 95)


def estimate_gbm_parameters(closes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """From daily closes (rows = days, columns = stocks) estimate each stock's average daily
    log return and the covariance matrix of daily log returns (volatility + how stocks move together)."""
    log_returns = np.diff(np.log(closes), axis=0)
    mean_log_returns = log_returns.mean(axis=0)
    covariance = np.atleast_2d(np.cov(log_returns, rowvar=False))
    return mean_log_returns, covariance


def simulate_portfolio_values(
    position_values: np.ndarray,
    cash: float,
    mean_log_returns: np.ndarray,
    covariance: np.ndarray,
    days: int,
    simulations: int,
    seed: int | None = None,
) -> np.ndarray:
    """Simulates `simulations` possible futures, `days` trading days long.

    Returns an array of shape (days, simulations): total portfolio value (cash + holdings) on each day of each future.
    """
    rng = np.random.default_rng(seed)
    # Cholesky turns independent random numbers into correlated ones that match the covariance.
    # The tiny extra on the diagonal keeps it working when stocks are perfectly (anti-)correlated.
    cholesky = np.linalg.cholesky(covariance + np.eye(len(covariance)) * 1e-12)

    cumulative_log_returns = np.zeros((simulations, len(position_values)))
    values_by_day = np.empty((days, simulations))
    for day in range(days):
        random_shocks = rng.standard_normal((simulations, len(position_values))) @ cholesky.T
        cumulative_log_returns += mean_log_returns + random_shocks
        values_by_day[day] = cash + (position_values * np.exp(cumulative_log_returns)).sum(axis=1)
    return values_by_day