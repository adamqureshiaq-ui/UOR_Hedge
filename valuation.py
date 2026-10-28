"""The single definition of how holdings are valued, shared by /portfolio and /leaderboard."""


def calculate_holdings_value(holdings, prices: dict[str, float]) -> float:
    """Current market value of a list of Portfolio rows, given {symbol: price}.

    An estimate for display and ranking (live prices are floats), so float maths is fine here.
    """
    return sum(float(holding.quantity) * prices[holding.symbol] for holding in holdings)