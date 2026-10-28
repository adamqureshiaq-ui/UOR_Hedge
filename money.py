"""Exact arithmetic for stored money and share quantities.

Floats can't represent most decimal numbers exactly (0.3 - 0.1 == 0.19999999999999998), and those
tiny errors pile up in balances. Every value that is stored or moved between accounts uses Decimal instead.
"""
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
SHARE_PRECISION = Decimal("0.000001")  # quantities are stored to 6 decimal places


def to_decimal(value: float) -> Decimal:
    """Turn a float from Alpaca (e.g. 150.05) into the exact Decimal it was meant to be."""
    return Decimal(str(value))


def round_money(value: Decimal) -> Decimal:
    """Round to whole cents, halves rounding up (2.345 -> 2.35), as a broker settles a trade."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def round_shares(value: Decimal) -> Decimal:
    return value.quantize(SHARE_PRECISION, rounding=ROUND_HALF_UP)