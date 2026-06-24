"""Fallback: fetch OI and volume via yfinance when Robinhood MCP returns empty.

Scans all JSON files in scripts/sourced_data/, reads ticker + expiration
from each, groups by ticker to avoid redundant yfinance calls, and patches
volume/open_interest onto each option entry.

Also computes IV Rank and IV Percentile for each ticker using rolling 30-day
historical volatility as a proxy (downloaded via yfinance).
"""

import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from yfinance import Ticker

SOURCED_DIR = Path(__file__).parent / "sourced_data"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _percentile_of_score(data, value):
    """Return the percentile (0-100) of *value* within *data*."""
    if data is None or len(data) == 0:
        return None
    count_le = sum(1 for x in data if x <= value)
    return count_le / len(data) * 100


def compute_iv_stats(ticker, current_iv):
    """Compute IV Rank & IV Percentile using rolling 30d HV as a proxy for IV.

    Downloads 1 year of daily OHLCV via yfinance, computes rolling 30-day
    annualized HV (as a decimal), then ranks *current_iv* against that
    distribution.

    Parameters
    ----------
    ticker : str
        Stock symbol (e.g. ``"SMH"``).
    current_iv : float | None
        Current ATM implied volatility as a decimal (e.g. ``0.58``).

    Returns
    -------
    dict | None
        Keys: ``iv_rank``, ``iv_percentile``, ``hv_high_52w``, ``hv_low_52w``,
        ``num_readings``.  Returns *None* when data is insufficient or inputs
        are invalid.
    """
    if not ticker or current_iv is None:
        return None

    t = Ticker(ticker)
    hist = t.history(period="1y")
    if hist.empty or len(hist) < 60:
        return None

    closes = hist["Close"].values
    log_returns = np.diff(np.log(closes))

    window = 30
    rv_list = []
    for i in range(window, len(log_returns) + 1):
        rv_list.append(np.std(log_returns[i - window: i]) * np.sqrt(252))

    rv = np.array(rv_list)
    rv = rv[np.isfinite(rv)]
    if len(rv) == 0:
        return None

    iv = float(current_iv)
    hv_range = rv.max() - rv.min()
    iv_rank = 50.0 if hv_range < 1e-10 else (iv - rv.min()) / hv_range * 100
    iv_rank = min(max(iv_rank, 0.0), 100.0)
    iv_percentile = _percentile_of_score(rv, iv)

    return {
        "iv_rank": round(iv_rank, 1),
        "iv_percentile": round(iv_percentile, 1),
        "hv_high_52w": round(rv.max() * 100, 1),
        "hv_low_52w": round(rv.min() * 100, 1),
        "num_readings": len(rv),
    }


def _avg_atm_iv(data):
    """Return average IV of the 4 strikes closest to stock_price."""
    stock_price = data.get("stock_price")
    if not stock_price or "options" not in data or not data["options"]:
        return None
    pairs = []
    for opt in data["options"]:
        iv = opt.get("iv")
        if iv is not None and iv > 0:
            pairs.append((abs(opt["strike"] - stock_price), iv))
    if not pairs:
        return None
    pairs.sort(key=lambda x: x[0])
    return sum(v for _, v in pairs[:4]) / min(len(pairs[:4]), 4)


# ---------------------------------------------------------------------------
# OI / Volume patching
# ---------------------------------------------------------------------------

def _patch(fp, opt):
    """Patch OI/volume on the JSON at *fp* using a yfinance Option object."""
    data = json.loads(fp.read_text())
    lookup = {}
    for _, row in opt.calls.iterrows():
        vol = int(row["volume"]) if row["volume"] == row["volume"] else 0
        lookup[(row["strike"], "call")] = (vol, int(row["openInterest"]))
    for _, row in opt.puts.iterrows():
        vol = int(row["volume"]) if row["volume"] == row["volume"] else 0
        lookup[(row["strike"], "put")] = (vol, int(row["openInterest"]))
    for entry in data["options"]:
        key = (entry["strike"], entry["type"])
        vol, oi = lookup.get(key, (0, 0))
        entry["volume"] = vol
        entry["open_interest"] = oi
    fp.write_text(json.dumps(data, indent=4))
    print(f"  Patched {fp.name}: {len(data['options'])} entries")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    files = sorted(SOURCED_DIR.glob("*.json"))
    if not files:
        print("No JSON files found in sourced_data/")
        return

    # Group by ticker so we create one Ticker per underlying
    groups = defaultdict(list)
    for fp in files:
        data = json.loads(fp.read_text())
        ticker = data.get("ticker")
        expiry = data.get("expiration")
        if not ticker or not expiry:
            print(f"  Skip {fp.name}: missing ticker or expiration")
            continue
        groups[ticker].append((expiry, fp))

    # Cache Ticker objects by ticker symbol
    ticker_cache = {}

    for ticker, pairs in groups.items():
        if ticker not in ticker_cache:
            ticker_cache[ticker] = Ticker(ticker)
        t = ticker_cache[ticker]

        seen_expiries = set()
        for expiry, fp in pairs:
            if expiry in seen_expiries:
                print(f"  Skip {fp.name}: expiry {expiry} already processed for {ticker}")
                continue
            seen_expiries.add(expiry)
            opt = t.option_chain(expiry)
            _patch(fp, opt)

        # --- IV Rank & Percentile ---
        avg_ivs = []
        for _, fp in pairs:
            data = json.loads(fp.read_text())
            aiv = _avg_atm_iv(data)
            if aiv is not None:
                avg_ivs.append(aiv)
        if avg_ivs:
            current_iv = sum(avg_ivs) / len(avg_ivs)
            stats = compute_iv_stats(ticker, current_iv)
            if stats:
                print(f"\n  IV Profile for {ticker}:")
                print(f"    IV Rank: {stats['iv_rank']}%")
                print(f"    IV Percentile: {stats['iv_percentile']}%")
                print(f"    52-Week HV Range: {stats['hv_low_52w']}% - {stats['hv_high_52w']}%")
                print(f"    Readings: {stats['num_readings']}")
            else:
                print(f"\n  IV Profile for {ticker}: insufficient data (<60 trading days)")
        print()


if __name__ == "__main__":
    main()
