#!/usr/bin/env python3
"""
Shared statistics and payoff helpers for the Options Strategy Advisor.

Provides reusable math for term-structure reports and At-Expiry payoff
matrices.  All functions are pure and importable (no CLI) so they can be
shared between ``termstructure_stats.py``, ``payoff_matrix.py`` and the test
suite.

Lognormal probability model:
    z = ln(level / spot) / (sigma * sqrt(T)),  T = dte / 365
    P(above) = 1 - Phi(z),  P(below) = Phi(z)

Expected move (1SD):
    EM = spot * sigma * sqrt(T)
"""

import math
from datetime import date
from math import erf, log, sqrt


# ---------------------------------------------------------------------------
# Normal / lognormal helpers
# ---------------------------------------------------------------------------

def ndist(x):
    """Standard normal CDF via erf."""
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def prob_above(level, spot, iv, dte):
    """Lognormal probability the underlying finishes above *level*."""
    if iv <= 0 or dte <= 0 or spot <= 0:
        return 0.0
    t = dte / 365.0
    z = log(level / spot) / (iv * sqrt(t))
    return 1.0 - ndist(z)


def prob_below(level, spot, iv, dte):
    """Lognormal probability the underlying finishes below *level*."""
    return 1.0 - prob_above(level, spot, iv, dte)


def expected_move(spot, iv, dte):
    """Return (move, lower, upper) for a 1SD expected move."""
    if iv <= 0 or dte <= 0 or spot <= 0:
        return 0.0, spot, spot
    t = dte / 365.0
    move = spot * iv * sqrt(t)
    return move, spot - move, spot + move


def avg_atm_iv(data, n=4):
    """Average IV of the *n* strikes nearest the stock price.

    Mirrors fetch_oi_volume.py's `_avg_atm_iv`.  Returns None when no
    valid IVs exist.
    """
    stock_price = data.get("stock_price")
    options = data.get("options")
    if not stock_price or not options:
        return None
    pairs = []
    for opt in options:
        iv = opt.get("iv")
        if iv is not None and iv > 0:
            pairs.append((abs(opt.get("strike", 0) - stock_price), iv))
    if not pairs:
        return None
    pairs.sort(key=lambda x: x[0])
    closest = pairs[:n]
    return sum(v for _, v in closest) / len(closest)


def resolve_dte(data, fallback=None):
    """Resolve days-to-expiration from a market-data dict.

    Order of preference: ``dte`` key -> computed from ``expiration`` vs today
    -> explicit *fallback* (CLI override).
    """
    dte = data.get("dte")
    if dte is not None and dte > 0:
        return int(dte)
    expiration = data.get("expiration")
    if expiration:
        try:
            exp = date.fromisoformat(str(expiration)[:10])
            return max(0, (exp - date.today()).days)
        except ValueError:
            pass
    return int(fallback) if fallback else 0


# ---------------------------------------------------------------------------
# Strategy payoff functions  (L = underlying price at expiry)
# ---------------------------------------------------------------------------

def straddle_payoff(L, strike, cost):
    """Long ATM straddle: |L - K| - cost."""
    return abs(L - strike) - cost


def bull_call_payoff(L, strike_low, strike_high, cost):
    """Long call vertical (buy low strike, sell high strike)."""
    return max(0.0, L - strike_low) - max(0.0, L - strike_high) - cost


def bear_put_payoff(L, strike_high, strike_low, cost):
    """Long put vertical (buy high strike, sell low strike)."""
    return max(0.0, strike_high - L) - max(0.0, strike_low - L) - cost


def short_put_payoff(L, strike, credit):
    """Short put (cash-secured): keep credit unless assigned."""
    return credit - max(0.0, strike - L)


# ---------------------------------------------------------------------------
# Payoff labeling  (vocabulary used in report payoff tables)
# ---------------------------------------------------------------------------

def payoff_label(value, max_profit=None, max_loss=None, eps=0.001):
    """Map a strategy P/L value to a report label.

    Labels: Max Gain / Max Loss / Gain / Lose / Partial Gain.
    """
    if max_profit is not None and value >= max_profit - eps:
        return "Max Gain"
    if max_loss is not None and value <= max_loss + eps:
        return "Max Loss"
    if value > 0:
        return "Gain"
    if value < 0:
        return "Lose"
    return "Partial Gain"


def short_put_label(value, credit, eps=0.001):
    """Label for a short put: Assigned / Keep Premium / Partial Gain."""
    if value < 0:
        return "Assigned"
    if value >= credit - eps:
        return "Keep Premium"
    return "Partial Gain"
