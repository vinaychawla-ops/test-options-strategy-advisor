#!/usr/bin/env python3
"""
Term Structure Statistics for Options Strategy Advisor.

Consumes one or more market-data JSONs (the same schema used by
calculate_gex.py / black_scholes.py) and prints the report analytics that the
Black-Scholes / GEX scripts do not produce:

  - Expected Move (1SD) and range per expiration
  - Lognormal probabilities (P above / below each level)
  - Put/Call volume and open-interest ratios
  - Per-strike open interest & volume tables
  - Put - Call IV skew tables

Usage:
  C:\\Python314\\python.exe scripts\\termstructure_stats.py --market-data scripts\\sourced_data\\spcx_0d.json scripts\\sourced_data\\spcx_30d.json scripts\\sourced_data\\spcx_60d.json
  C:\\Python314\\python.exe scripts\\termstructure_stats.py --market-data data.json --levels 120 130 140 150
  C:\\Python314\\python.exe scripts\\termstructure_stats.py --market-data data.json --dte 30 --spot 393.33 --format markdown
"""

import argparse
import json
import sys
from pathlib import Path

from statistics import avg_atm_iv, expected_move, prob_above, prob_below, resolve_dte


# ---------------------------------------------------------------------------
# Per-file analysis
# ---------------------------------------------------------------------------

def analyze(data):
    """Compute all statistics for a single market-data dict."""
    spot = data.get("stock_price")
    options = data.get("options", [])
    dte = resolve_dte(data, None)
    iv = avg_atm_iv(data)

    return {
        "ticker": data.get("ticker", "?"),
        "expiration": data.get("expiration", "?"),
        "dte": dte,
        "spot": spot,
        "iv": iv,
        "options": options,
    }


def pc_ratios(options):
    """Return (call_vol, put_vol, pc_vol, call_oi, put_oi, pc_oi)."""
    cv = sum(o.get("volume", 0) for o in options if o.get("type", "").lower() == "call")
    pv = sum(o.get("volume", 0) for o in options if o.get("type", "").lower() == "put")
    co = sum(o.get("open_interest", 0) for o in options if o.get("type", "").lower() == "call")
    po = sum(o.get("open_interest", 0) for o in options if o.get("type", "").lower() == "put")
    pc_vol = pv / cv if cv else None
    pc_oi = po / co if co else None
    return cv, pv, pc_vol, co, po, pc_oi


def per_strike_rows(options):
    """Return rows: (strike, call_vol, put_vol, call_oi, put_oi, call_iv, put_iv)."""
    by_strike = {}
    for o in options:
        strike = o.get("strike")
        if strike is None:
            continue
        entry = by_strike.setdefault(strike, {"call_vol": 0, "put_vol": 0, "call_oi": 0, "put_oi": 0, "call_iv": None, "put_iv": None})
        if o.get("type", "").lower() == "call":
            entry["call_vol"] += o.get("volume", 0)
            entry["call_oi"] += o.get("open_interest", 0)
            if o.get("iv") is not None:
                entry["call_iv"] = o["iv"]
        elif o.get("type", "").lower() == "put":
            entry["put_vol"] += o.get("volume", 0)
            entry["put_oi"] += o.get("open_interest", 0)
            if o.get("iv") is not None:
                entry["put_iv"] = o["iv"]
    rows = []
    for strike in sorted(by_strike):
        e = by_strike[strike]
        rows.append((strike, e["call_vol"], e["put_vol"], e["call_oi"], e["put_oi"], e["call_iv"], e["put_iv"]))
    return rows


def default_levels(options):
    """Round levels spanning the strike range (fallback when --levels absent)."""
    strikes = [o.get("strike") for o in options if o.get("strike") is not None]
    if not strikes:
        return []
    lo, hi = min(strikes), max(strikes)
    return [s for s in range(int(lo // 5 * 5), int(hi // 5 * 5) + 1, 5) if s >= lo and s <= hi]


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def fmt_pct(x):
    return "N/A" if x is None else f"{x * 100:.1f}%"


def _fmt_row(cells, widths):
    return " | ".join(str(c).rjust(w) for c, w in zip(cells, widths))


def render_text(analysis, levels):
    out = []
    for a in analysis:
        out.append("=" * 72)
        out.append(f"  {a['ticker']}  ({a['expiration']}, {a['dte']} DTE)")
        out.append("=" * 72)
        out.append(f"  Spot: ${a['spot']:.2f}    Avg ATM IV: {fmt_pct(a['iv'])}")
        out.append("")

        # Expected move
        if a["iv"]:
            move, lo, hi = expected_move(a["spot"], a["iv"], a["dte"])
            out.append(f"  Expected Move (1SD): ${move:.2f}  range ${lo:.2f} - ${hi:.2f}")
            out.append("")

        # Probabilities
        out.append("  PROBABILITIES (lognormal)")
        out.append("  " + "-" * 40)
        out.append(f"  {'Level':>10} {'P(above)':>10} {'P(below)':>10}")
        for lvl in levels:
            pa = prob_above(lvl, a["spot"], a["iv"], a["dte"])
            out.append(f"  {lvl:>10.2f} {pa * 100:>9.1f}% {prob_below(lvl, a['spot'], a['iv'], a['dte']) * 100:>9.1f}%")
        out.append("")

        # PC ratios
        cv, pv, pc_vol, co, po, pc_oi = pc_ratios(a["options"])
        out.append("  PUT/CALL RATIOS")
        out.append("  " + "-" * 40)
        out.append(f"  Call Vol: {cv}   Put Vol: {pv}   PC Vol: {fmt_pct(pc_vol)}")
        out.append(f"  Call OI:  {co}   Put OI:  {po}   PC OI:  {fmt_pct(pc_oi)}")
        out.append("")

        # Per-strike table
        rows = per_strike_rows(a["options"])
        out.append("  PER-STRIKE OI / VOLUME / IV")
        out.append("  " + "-" * 72)
        out.append(f"  {'Strike':>8} {'C-Vol':>7} {'P-Vol':>7} {'C-OI':>7} {'P-OI':>7} {'C-IV':>7} {'P-IV':>7} {'Put-Call':>9}")
        for strike, cvol, pvol, coi, poi, civ, piv in rows:
            skew = (piv - civ) * 100 if civ is not None and piv is not None else None
            out.append(f"  {strike:>8.2f} {cvol:>7} {pvol:>7} {coi:>7} {poi:>7} "
                       f"{fmt_pct(civ):>7} {fmt_pct(piv):>7} "
                       f"{('N/A' if skew is None else f'{skew:+.1f}pp'):>9}")
        out.append("")
    return "\n".join(out)


def render_markdown(analysis, levels):
    out = []
    for a in analysis:
        out.append(f"### {a['ticker']} ({a['expiration']}, {a['dte']} DTE)")
        out.append("")
        out.append(f"| Spot | Avg ATM IV | 1SD Move | Range |")
        out.append("|:---:|:---:|:---:|:---:|")
        if a["iv"]:
            move, lo, hi = expected_move(a["spot"], a["iv"], a["dte"])
            out.append(f"| ${a['spot']:.2f} | {fmt_pct(a['iv'])} | ${move:.2f} | ${lo:.2f} - ${hi:.2f} |")
        out.append("")

        out.append("#### Lognormal Probabilities")
        out.append("")
        out.append("| Level | P(above) | P(below) |")
        out.append("|-------:|:---:|:---:|")
        for lvl in levels:
            out.append(f"| {lvl:.2f} | {prob_above(lvl, a['spot'], a['iv'], a['dte']) * 100:.1f}% | "
                       f"{prob_below(lvl, a['spot'], a['iv'], a['dte']) * 100:.1f}% |")
        out.append("")

        cv, pv, pc_vol, co, po, pc_oi = pc_ratios(a["options"])
        out.append("#### Put/Call Ratios")
        out.append("")
        out.append(f"| Call Vol | Put Vol | PC Vol | Call OI | Put OI | PC OI |")
        out.append("|:---:|:---:|:---:|:---:|:---:|:---:|")
        out.append(f"| {cv} | {pv} | {fmt_pct(pc_vol)} | {co} | {po} | {fmt_pct(pc_oi)} |")
        out.append("")

        out.append("#### Per-Strike OI / Volume / IV")
        out.append("")
        out.append("| Strike | C-Vol | P-Vol | C-OI | P-OI | C-IV | P-IV | Put-Call |")
        out.append("|---:|---:|---:|---:|---:|---:|---:|---:|")
        for strike, cvol, pvol, coi, poi, civ, piv in per_strike_rows(a["options"]):
            skew = (piv - civ) * 100 if civ is not None and piv is not None else None
            out.append(f"| {strike:.2f} | {cvol} | {pvol} | {coi} | {poi} | {fmt_pct(civ)} | {fmt_pct(piv)} | "
                       f"{('N/A' if skew is None else f'{skew:+.1f}pp')} |")
        out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Term-structure stats (expected move, probabilities, PC ratios, OI/volume, IV skew) "
                    "from market-data JSONs.",
        epilog=(
            "  python scripts/termstructure_stats.py --market-data data_0d.json data_30d.json data_60d.json\n"
            "  python scripts/termstructure_stats.py --market-data data.json --levels 120 130 140 150\n"
        ),
    )
    parser.add_argument("--market-data", type=str, nargs="+", required=True,
                        help="One or more market-data JSON files (stock_price + options array)")
    parser.add_argument("--levels", type=float, nargs="+", default=None,
                        help="Price levels for probability table (default: strikes spanning range)")
    parser.add_argument("--dte", type=int, default=None,
                        help="Days-to-expiration override when JSON lacks 'dte'/'expiration'")
    parser.add_argument("--spot", type=float, default=None,
                        help="Stock price override (default: from JSON)")
    parser.add_argument("--format", type=str, choices=["text", "markdown"], default="text",
                        help="Output format (default: text)")

    args = parser.parse_args(argv)

    analysis = []
    for path in args.market_data:
        try:
            with open(path) as f:
                data = json.load(f)
        except Exception as e:
            print(f"Warning: could not load {path}: {e}", file=sys.stderr)
            continue
        if args.spot is not None:
            data["stock_price"] = args.spot
        if args.dte is not None:
            data["dte"] = args.dte
        analysis.append(analyze(data))

    if not analysis:
        print("No market data loaded.", file=sys.stderr)
        return 1

    # Levels default from first file's strike range
    if args.levels is None:
        levels = default_levels(analysis[0]["options"])
    else:
        levels = args.levels

    if args.format == "markdown":
        print(render_markdown(analysis, levels))
    else:
        print(render_text(analysis, levels))
    return 0


if __name__ == "__main__":
    sys.exit(main())
