#!/usr/bin/env python3
"""
At-Expiry Payoff Matrix for Options Strategy Advisor.

Computes payoff tables for analyst-specified strategies across a set of
underlying price levels at expiry, using the shared payoff functions in
``statistics.py``.  Strategies are supplied as a JSON file because the
strikes / costs are per-report analyst choices that cannot be inferred from
market data alone.

Strategy JSON schema (``--strategies``):
    [
      {"name": "Long Straddle 135", "type": "straddle", "strike": 135, "cost": 24.10},
      {"name": "Bull Call 130/140", "type": "bull_call",
       "strike_low": 130, "strike_high": 140, "cost": 4.13,
       "max_profit": 5.87, "max_loss": -4.13},
      {"name": "Bear Put 135/130", "type": "bear_put",
       "strike_low": 130, "strike_high": 135, "cost": 2.83,
       "max_profit": 2.17, "max_loss": -2.83},
      {"name": "Short Put 125", "type": "short_put", "strike": 125, "credit": 7.78}
    ]

Supported ``type`` values: straddle | bull_call | bear_put | short_put.

Usage:
  C:\\Python314\\python.exe scripts\\payoff_matrix.py --market-data scripts\\sourced_data\\spcx_30d.json --strategies strategies.json
  C:\\Python314\\python.exe scripts\\payoff_matrix.py --market-data data.json --strategies s.json --levels 100 120 135 170
  C:\\Python314\\python.exe scripts\\payoff_matrix.py --market-data data.json --strategies s.json --probability
"""

import argparse
import json
import sys
from pathlib import Path

from statistics import (
    avg_atm_iv,
    bear_put_payoff,
    bull_call_payoff,
    payoff_label,
    prob_above,
    prob_below,
    resolve_dte,
    short_put_label,
    short_put_payoff,
    straddle_payoff,
)


# ---------------------------------------------------------------------------
# Strategy dispatch
# ---------------------------------------------------------------------------

def payoff_for(strategy, L):
    """Compute strategy payoff at underlying level L (P/L in dollars)."""
    stype = strategy.get("type")
    if stype == "straddle":
        return straddle_payoff(L, strategy["strike"], strategy["cost"])
    if stype == "bull_call":
        return bull_call_payoff(L, strategy["strike_low"], strategy["strike_high"], strategy["cost"])
    if stype == "bear_put":
        return bear_put_payoff(L, strategy["strike_high"], strategy["strike_low"], strategy["cost"])
    if stype == "short_put":
        return short_put_payoff(L, strategy["strike"], strategy["credit"])
    raise ValueError(f"unknown strategy type: {stype}")


def label_for(strategy, value):
    """Report label for a strategy payoff value."""
    if strategy.get("type") == "short_put":
        return short_put_label(value, strategy["credit"])
    return payoff_label(value, strategy.get("max_profit"), strategy.get("max_loss"))


def breakevens(strategy):
    """Return a list of breakeven price(s) for the strategy."""
    stype = strategy.get("type")
    if stype == "straddle":
        return [strategy["strike"] - strategy["cost"], strategy["strike"] + strategy["cost"]]
    if stype == "bull_call":
        return [strategy["strike_low"] + strategy["cost"]]
    if stype == "bear_put":
        return [strategy["strike_high"] - strategy["cost"]]
    if stype == "short_put":
        return [strategy["strike"] - strategy["credit"]]
    return []


def prob_of_profit(strategy, spot, iv, dte):
    """Lognormal probability the strategy is profitable at expiry."""
    if not iv or not dte:
        return None
    stype = strategy.get("type")
    if stype == "straddle":
        lo, hi = breakevens(strategy)
        return prob_below(lo, spot, iv, dte) + prob_above(hi, spot, iv, dte)
    if stype == "bull_call":
        (be,) = breakevens(strategy)
        return prob_above(be, spot, iv, dte)
    if stype == "bear_put":
        (be,) = breakevens(strategy)
        return prob_below(be, spot, iv, dte)
    if stype == "short_put":
        (be,) = breakevens(strategy)
        return prob_above(be, spot, iv, dte)
    return None


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def render_text(strategies, levels, probs):
    header = f"{'Level':>8} | " + " | ".join(s["name"] for s in strategies)
    sep = "-" * len(header)
    lines = [header, sep]
    for L in levels:
        cells = [f"{L:>8}"]
        for i, s in enumerate(strategies):
            v = payoff_for(s, L)
            lab = label_for(s, v)
            cells.append(f"${v:>7.2f} {lab:>12}")
        lines.append(" | ".join(cells))
    lines.append("")
    if probs:
        lines.append(f"{'Prob of Profit':>8} | " + " | ".join(
            f"{p * 100:>6.1f}%" if p is not None else "    N/A" for p in probs))
        lines.append("")
    return "\n".join(lines)


def render_markdown(strategies, levels, probs):
    lines = []
    lines.append("| Level | " + " | ".join(s["name"] for s in strategies) + " |")
    lines.append("|---:|" + "|".join(["---"] * len(strategies)) + "|")
    for L in levels:
        cells = [f"{L:.2f}"]
        for s in strategies:
            v = payoff_for(s, L)
            cells.append(label_for(s, v))
        lines.append("| " + " | ".join(cells) + " |")
    if probs:
        cells = ["Prob of Profit"]
        for p in probs:
            cells.append(f"{p * 100:.1f}%" if p is not None else "N/A")
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="At-Expiry payoff matrix for analyst-specified strategies.",
        epilog=(
            "  python scripts/payoff_matrix.py --market-data data_30d.json --strategies strategies.json\n"
            "  python scripts/payoff_matrix.py --market-data data.json --strategies s.json --probability\n"
        ),
    )
    parser.add_argument("--market-data", type=str, required=True,
                        help="Market-data JSON (used for spot / IV / DTE context)")
    parser.add_argument("--strategies", type=str, required=True,
                        help="JSON file with strategy definitions")
    parser.add_argument("--levels", type=float, nargs="+", default=None,
                        help="Underlying price levels for the payoff rows")
    parser.add_argument("--probability", action="store_true", default=False,
                        help="Add a probability-of-profit row using IV/DTE from market data")
    parser.add_argument("--format", type=str, choices=["text", "markdown"], default="text",
                        help="Output format (default: text)")

    args = parser.parse_args(argv)

    try:
        with open(args.market_data) as f:
            data = json.load(f)
    except Exception as e:
        print(f"Could not load market data {args.market_data}: {e}", file=sys.stderr)
        return 1

    try:
        with open(args.strategies) as f:
            strategies = json.load(f)
    except Exception as e:
        print(f"Could not load strategies {args.strategies}: {e}", file=sys.stderr)
        return 1

    spot = data.get("stock_price")
    iv = avg_atm_iv(data)
    dte = resolve_dte(data, None)

    levels = args.levels or [s.get("level") for s in strategies if s.get("level")] or []
    if not levels:
        print("No --levels provided and no 'level' keys in strategies.", file=sys.stderr)
        return 1

    probs = None
    if args.probability:
        probs = [prob_of_profit(s, spot, iv, dte) for s in strategies]

    print(f"Spot: ${spot:.2f}  Avg ATM IV: "
          f"{('N/A' if iv is None else f'{iv * 100:.1f}%')}  DTE: {dte}\n")
    if args.format == "markdown":
        print(render_markdown(strategies, levels, probs))
    else:
        print(render_text(strategies, levels, probs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
