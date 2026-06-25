#!/usr/bin/env python3
"""
GEX (Gamma Exposure) Calculator

Computes Gamma Exposure levels from options market data fetched via Robinhood MCP
(Bid/Ask/IV/Greeks) and yfinance fallback (Open Interest, Volume).

Formula (SpotGamma):
  GEX = Gamma x Open Interest x 100 x Spot Price^2
  Calls: positive sign (dealers are long gamma -> stabilizing)
  Puts:  negative sign (dealers are short gamma -> amplifying)

Only computes values from actually fetched data.  If gamma or open_interest is
missing/zero on a contract, that contract is skipped.  If no valid contracts
exist, all metrics report N/A.

Usage:
  C:\\Python314\\python.exe scripts\\calculate_gex.py --market-data scripts\\sourced_data\\avgo_30d.json
  C:\\Python314\\python.exe scripts\\calculate_gex.py --market-data data.json --stock-price 393.33
  C:\\Python314\\python.exe scripts\\calculate_gex.py --market-data data.json --output output\\gex_avgo.json
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


class GEXCalculator:
    """Gamma Exposure calculator.  Only uses values present in the input data."""

    def __init__(self, options, stock_price):
        self.options = options
        self.stock_price = stock_price
        self.contracts = []
        self.data_quality = {
            "total_options": len(options),
            "valid_options": 0,
            "skipped_no_gamma": 0,
            "skipped_no_oi": 0,
        }
        self._compute()

    # ------------------------------------------------------------------
    # Core computation
    # ------------------------------------------------------------------

    def _compute(self):
        for opt in self.options:
            gamma = opt.get("gamma")
            oi = opt.get("open_interest")
            strike = opt.get("strike")
            opt_type = opt.get("type", "").lower()

            if gamma is None or gamma <= 0:
                self.data_quality["skipped_no_gamma"] += 1
                continue

            if oi is None or oi <= 0:
                self.data_quality["skipped_no_oi"] += 1
                continue

            gex_value = gamma * oi * 100 * self.stock_price ** 2

            if opt_type == "put":
                gex_value = -gex_value

            self.contracts.append({
                "strike": strike,
                "type": opt_type,
                "gamma": gamma,
                "open_interest": oi,
                "gex": gex_value,
            })

            self.data_quality["valid_options"] += 1

    # ------------------------------------------------------------------
    # Aggregate Metrics  (all return None when data is insufficient)
    # ------------------------------------------------------------------

    def net_gex(self):
        if not self.contracts:
            return None
        return sum(c["gex"] for c in self.contracts)

    def abs_gex(self):
        if not self.contracts:
            return None
        return sum(abs(c["gex"]) for c in self.contracts)

    def gex_per_1pct(self):
        net = self.net_gex()
        if net is None:
            return None
        return net * 0.01

    def call_contracts(self):
        return [c for c in self.contracts if c["type"] == "call"]

    def put_contracts(self):
        return [c for c in self.contracts if c["type"] == "put"]

    def total_call_gex(self):
        calls = self.call_contracts()
        return sum(c["gex"] for c in calls) if calls else 0.0

    def total_put_gex(self):
        puts = self.put_contracts()
        return sum(c["gex"] for c in puts) if puts else 0.0

    def call_wall(self):
        """Strike with the highest call GEX concentration."""
        calls = self.call_contracts()
        if not calls:
            return None
        return max(calls, key=lambda c: c["gex"])["strike"]

    def put_wall(self):
        """Strike with the highest (absolute) put GEX concentration."""
        puts = self.put_contracts()
        if not puts:
            return None
        return max(puts, key=lambda c: abs(c["gex"]))["strike"]

    def gamma_flip(self):
        """Interpolated strike where cumulative net GEX crosses zero.

        Strikes are sorted ascending.  Cumulative net GEX is summed from the
        lowest strike upward.  When the cumulative sum crosses zero, we linearly
        interpolate between the straddling strikes to find the exact flip level.

        Returns None when there are fewer than 2 strikes or the cumulative sum
        never crosses zero within the observed range.
        """
        if len(self.contracts) < 2:
            return None

        strike_map = {}
        for c in self.contracts:
            s = c["strike"]
            strike_map[s] = strike_map.get(s, 0.0) + c["gex"]

        sorted_strikes = sorted(strike_map.items())
        if len(sorted_strikes) < 2:
            return None

        cumulative = 0.0
        for i, (strike, gex) in enumerate(sorted_strikes):
            prev_cumulative = cumulative
            cumulative += gex

            if prev_cumulative < 0 and cumulative >= 0:
                fraction = -prev_cumulative / (cumulative - prev_cumulative)
                prev_strike = sorted_strikes[i - 1][0]
                return prev_strike + fraction * (strike - prev_strike)

            if prev_cumulative > 0 and cumulative <= 0:
                fraction = -prev_cumulative / (cumulative - prev_cumulative)
                prev_strike = sorted_strikes[i - 1][0]
                return prev_strike + fraction * (strike - prev_strike)

        return None

    # ------------------------------------------------------------------
    # Regime classification
    # ------------------------------------------------------------------

    def regime(self):
        net = self.net_gex()
        flip = self.gamma_flip()

        if net is None:
            return "N/A \u2014 insufficient data"

        if net > 0:
            return "POSITIVE GEX \u2014 Stabilizing. Dealers buy dips, sell rallies."

        if net < 0:
            return "NEGATIVE GEX \u2014 Amplifying. Dealers amplify momentum."

        return "NEUTRAL GEX \u2014 Transition zone."

    # ------------------------------------------------------------------
    # Strike-level profile
    # ------------------------------------------------------------------

    def strike_profile(self):
        """Aggregate call + put GEX per strike, sorted ascending."""
        strike_map = {}
        for c in self.contracts:
            s = c["strike"]
            if s not in strike_map:
                strike_map[s] = {"strike": s, "call_gex": 0.0, "put_gex": 0.0, "net_gex": 0.0}
            if c["type"] == "call":
                strike_map[s]["call_gex"] += c["gex"]
            else:
                strike_map[s]["put_gex"] += c["gex"]
            strike_map[s]["net_gex"] = strike_map[s]["call_gex"] + strike_map[s]["put_gex"]

        return sorted(strike_map.values(), key=lambda x: x["strike"])

    def _gex_bar(self, value, abs_max, width=25, char="#"):
        """Return an ASCII bar proportional to |value| / abs_max."""
        if abs_max is None or abs_max <= 0:
            return ""
        bar_len = int(min(abs(value) / abs_max * width, width))
        return char * bar_len

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self):
        strike_profile = self.strike_profile()
        abs_total = self.abs_gex()

        return {
            "generated_at": datetime.now().isoformat(),
            "stock_price": self.stock_price,
            "metrics": {
                "net_gex": self.net_gex(),
                "net_gex_1pct": self.gex_per_1pct(),
                "abs_gex": abs_total,
                "call_wall_strike": self.call_wall(),
                "put_wall_strike": self.put_wall(),
                "gamma_flip": self.gamma_flip(),
                "total_call_gex": self.total_call_gex(),
                "total_put_gex": self.total_put_gex(),
            },
            "regime": self.regime(),
            "strikes": [
                {
                    "strike": s["strike"],
                    "call_gex": s["call_gex"],
                    "put_gex": s["put_gex"],
                    "net_gex": s["net_gex"],
                    "pct_of_abs": round(
                        abs(s["net_gex"]) / abs_total * 100, 2
                    ) if abs_total and abs_total > 0 else 0.0,
                }
                for s in strike_profile
            ],
            "data_quality": self.data_quality,
        }


# =========================================================================
# Formatting Helpers
# =========================================================================

_DOLLAR_N_A = "N/A"


def _fmt_dollar(value):
    if value is None:
        return _DOLLAR_N_A
    if abs(value) >= 1_000_000:
        return f"${value:+,.0f}"
    if abs(value) >= 1_000:
        return f"${value:+,.0f}"
    return f"${value:+,.2f}"


def _fmt_compact(value):
    """Format in millions for the table columns."""
    if value is None:
        return _DOLLAR_N_A
    if abs(value) < 1_000:
        return f"${value:+,.2f}"
    millions = value / 1_000_000
    return f"${millions:+,.1f}M"


def _fmt_1pct(value):
    """Format per-1%-move figure."""
    if value is None:
        return _DOLLAR_N_A
    av = abs(value)
    if av >= 1_000_000:
        return f"${value / 1_000_000:+,.1f}M"
    if av >= 1_000:
        return f"${value / 1_000:+,.0f}K"
    return f"${value:+,.0f}"


def _label_or_na(value, prefix="$", suffix=""):
    if value is None:
        return "N/A"
    return f"{prefix}{value:.2f}{suffix}"


# =========================================================================
# Report Printing
# =========================================================================


def print_report(calc, ticker=None, expiration=None, dte=None):
    net = calc.net_gex()
    abs_total = calc.abs_gex()
    net_1pct = calc.gex_per_1pct()
    call_wall = calc.call_wall()
    put_wall = calc.put_wall()
    gamma_flip = calc.gamma_flip()
    stock_price = calc.stock_price
    strike_df = calc.strike_profile()

    # Header
    header = "GEX ANALYSIS"
    if ticker:
        header += f" \u2014 {ticker}"
    if expiration:
        header += f"  ({expiration}"
        header += f", {dte} DTE" if dte else ""
        header += ")"
    sep = "=" * 72

    print()
    print(sep)
    print(f"  {header}")
    print(sep)
    print()

    # ------------------------------------------------------------------
    # Summary metrics
    # ------------------------------------------------------------------
    print("  SUMMARY METRICS")
    print(f"  {'-' * 68}")
    print(f"    Stock Price:           {_label_or_na(stock_price)}")
    print(f"    Valid Contracts:       {calc.data_quality['valid_options']} / {calc.data_quality['total_options']} options")
    if calc.data_quality["skipped_no_gamma"]:
        print(f"    Skipped (no gamma):    {calc.data_quality['skipped_no_gamma']}")
    if calc.data_quality["skipped_no_oi"]:
        print(f"    Skipped (no OI):       {calc.data_quality['skipped_no_oi']}")
    print(f"    Net GEX:               {_fmt_compact(net):>20s}   (per 1%: {_fmt_1pct(net_1pct)})")
    print(f"    Absolute GEX:          {_fmt_compact(abs_total):>20s}")
    print(f"    Call GEX (total):      {_fmt_compact(calc.total_call_gex()):>20s}")
    print(f"    Put GEX (total):       {_fmt_compact(calc.total_put_gex()):>20s}")
    print(f"    Call Wall:             {_label_or_na(call_wall):>20s}")
    print(f"    Put Wall:              {_label_or_na(put_wall):>20s}")
    print(f"    Gamma Flip:            {_label_or_na(gamma_flip):>20s}")
    print()

    # ------------------------------------------------------------------
    # Regime callout
    # ------------------------------------------------------------------
    print(f"  REGIME: {calc.regime()}")
    if gamma_flip is not None and net is not None:
        if net > 0 and stock_price and stock_price > gamma_flip:
            print(f"    Stock (${stock_price:.2f}) is ABOVE Gamma Flip (${gamma_flip:.2f}) \u2014 dealers are net stabilizing.")
        elif net < 0 and stock_price and stock_price < gamma_flip:
            print(f"    Stock (${stock_price:.2f}) is BELOW Gamma Flip (${gamma_flip:.2f}) \u2014 dealers are net amplifying.")
        elif gamma_flip is not None and stock_price:
            print(f"    Stock (${stock_price:.2f}) vs Gamma Flip (${gamma_flip:.2f}) \u2014 regime in transition.")
    print()

    # ------------------------------------------------------------------
    # Per-strike profile
    # ------------------------------------------------------------------
    if not strike_df:
        print("  No valid options data available.")
        print()
        print(sep)
        print()
        return

    abs_max = max(
        max(abs(s["call_gex"]), abs(s["put_gex"])) for s in strike_df
    )

    print("  STRIKE GEX PROFILE")
    print(f"  {'-' * 68}")
    col_hdr = (
        f"  {'Strike':>8s}  "
        f"{'Call GEX':>14s}  "
        f"{'Put GEX':>14s}  "
        f"{'Net GEX':>14s}  "
        f"{'%Abs':>7s}"
    )
    print(col_hdr)
    print(f"  {'-' * (len(col_hdr) - 2)}")

    for s in strike_df:
        stk = s["strike"]
        cg = s["call_gex"]
        pg = s["put_gex"]
        ng = s["net_gex"]
        pct = (
            abs(ng) / abs_total * 100
            if abs_total and abs_total > 0
            else 0.0
        )
        print(
            f"  ${stk:>7.2f}  "
            f"{_fmt_compact(cg):>14s}  "
            f"{_fmt_compact(pg):>14s}  "
            f"{_fmt_compact(ng):>14s}  "
            f"{pct:>6.1f}%"
        )
    print()

    # ------------------------------------------------------------------
    # ASCII bar chart
    # ------------------------------------------------------------------
    bar_w = 20
    print("  GEX PROFILE  (C = Call GEX   P = Put GEX)")
    print(f"  {'-' * 68}")
    for s in strike_df:
        stk = s["strike"]
        c_bar = calc._gex_bar(s["call_gex"], abs_max, bar_w, "C")
        p_bar = calc._gex_bar(s["put_gex"], abs_max, bar_w, "P")
        c_bar = c_bar.ljust(bar_w)
        p_bar = p_bar.ljust(bar_w)
        print(f"  ${stk:>7.2f}  C{c_bar}  P{p_bar}")

    print()
    print(sep)
    print()


def save_json_output(data, filepath):
    fp = Path(filepath)
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(json.dumps(data, indent=2, default=str))
    print(f"  Saved GEX data to {fp}")


# =========================================================================
# CLI Entry Point
# =========================================================================


def main():
    parser = argparse.ArgumentParser(
        description="GEX (Gamma Exposure) Calculator \u2014 SpotGamma methodology.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  C:\\Python314\\python.exe scripts\\calculate_gex.py "
            "--market-data scripts\\sourced_data\\avgo_30d.json\n"
            "  C:\\Python314\\python.exe scripts\\calculate_gex.py "
            "--market-data data.json --stock-price 393.33\n"
            "  C:\\Python314\\python.exe scripts\\calculate_gex.py "
            "--market-data data.json --output output\\gex_avgo.json\n"
        ),
    )

    parser.add_argument(
        "--market-data",
        type=str,
        required=True,
        help="Path to JSON with stock_price + options[].  Each option needs: "
        "strike, type, gamma, open_interest.  (Fetched via Robinhood MCP + "
        "yfinance fallback.)",
    )
    parser.add_argument(
        "--stock-price",
        type=float,
        default=None,
        help="Override stock price from JSON.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Save GEX results as JSON (e.g. output/gex_avgo_30d.json).",
    )
    parser.add_argument(
        "--ticker",
        type=str,
        default=None,
        help="Override ticker symbol in report header.",
    )

    args = parser.parse_args()

    try:
        with open(args.market_data) as f:
            market_data = json.load(f)
    except Exception as e:
        print(f"Error: could not load market data from {args.market_data}: {e}")
        sys.exit(1)

    stock_price = args.stock_price
    if stock_price is None:
        stock_price = market_data.get("stock_price")
    if stock_price is None or stock_price <= 0:
        print("Error: no valid stock_price.  Provide --stock-price or include stock_price in JSON.")
        sys.exit(1)

    ticker = args.ticker or market_data.get("ticker")
    expiration = market_data.get("expiration")
    dte = market_data.get("dte")

    options = market_data.get("options", [])
    if not options:
        print("Warning: no options array in market data.  All GEX metrics will show N/A.")

    calc = GEXCalculator(options, stock_price)

    print_report(calc, ticker=ticker, expiration=expiration, dte=dte)

    if args.output:
        result = calc.to_dict()
        for k in ("ticker", "expiration", "dte"):
            v = market_data.get(k) or locals().get(k)
            if v is not None:
                result[k] = v
        save_json_output(result, args.output)


if __name__ == "__main__":
    main()
