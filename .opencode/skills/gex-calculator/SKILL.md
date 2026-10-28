---
name: gex-calculator
description: >-
  Gamma Exposure (GEX) analysis using SpotGamma methodology.
  Computes Net GEX, Absolute GEX, Call Wall, Put Wall, Gamma Flip,
  and per-strike GEX profiles from options market data fetched via
  Robinhood MCP and yfinance.  ZERO estimation — if gamma or
  open_interest is missing/zero/null, the contract is skipped and
  all affected metrics show N/A.
---

# GEX Calculator — Gamma Exposure Analysis

## Overview

**GEX (Gamma Exposure)** measures the total dollar value of stock that options
market makers must buy or sell to maintain delta-neutral hedges for every 1%
move in the underlying asset.

**Formula (SpotGamma):**
```
GEX = Gamma x Open Interest x 100 x Spot Price^2
```

**Sign convention:**
- **Calls**: positive GEX (dealers who sold calls are long gamma → stabilizing)
- **Puts**: negative GEX (dealers who sold puts are short gamma → amplifying)

### Core Principle — No Estimation

This tool **never estimates data**. Every GEX value comes from actually-fetched
`gamma` and `open_interest`. If a contract lacks either field, it is **skipped**
and the count is reported in `data_quality`. If all contracts are skipped, every
metric displays **N/A**. This applies to every script in the pipeline.

| Situation | What happens |
|-----------|--------------|
| `gamma` is missing, zero, or null | Contract skipped (`skipped_no_gamma`) |
| `open_interest` is missing, zero, or null | Contract skipped (`skipped_no_oi`) |
| Both missing | Contract skipped (counted once) |
| All contracts skipped | All metrics report N/A |
| Only some skipped | Only valid contracts used; skip count in `data_quality` |

## Data Requirements

| Field | Source | Required per contract? | If missing |
|-------|--------|-----------------------|------------|
| `gamma` | Robinhood MCP `get_option_quotes` (Greeks) | Yes | Skip contract |
| `open_interest` | Robinhood MCP `get_option_quotes` (returns OI directly) or yfinance via `fetch_oi_volume.py` | Yes | Skip contract |
| `stock_price` | Robinhood MCP `get_equity_quotes` or `--stock-price` | Yes (global) | Exit with error |
| `strike` | Robinhood MCP `get_option_instruments` | Yes (identifies the row) | Cannot calculate per-strike profile |
| `type` | Robinhood MCP `get_option_instruments` | Yes ("call" or "put") | Sign convention unknown; contract skipped |

**No proxy, no estimation:**
- Do NOT derive gamma from delta or IV — gamma must be a fetched value
- Do NOT impute open_interest from volume, bid/ask spread, or moneyness
- Do NOT fill missing fields with model outputs, historical averages, or simulation

## Prerequisites

**Required:**
- Python 3.8+ with `numpy`
- Robinhood MCP server (for market data used to build input JSONs)
- `open_interest` present on the source JSONs — from `get_option_quotes` (returned directly) or patched via `fetch_oi_volume.py`

**Supplied with this skill:**
- `scripts/calculate_gex.py` — GEX computation engine
- `scripts/gex_to_html.py` — HTML report renderer

**Not required:**
- No API keys needed (scripts read from already-fetched JSONs)
- No yfinance calls during GEX computation (OI already patched upstream)

## When to Use This Skill

Use this skill when:
- The user asks "what's the gamma exposure for X?"
- The user needs to know **Call Wall** (resistance) or **Put Wall** (support) levels
- The user asks whether the market is in a **stabilizing or amplifying regime**
- The user wants to understand **dealer positioning** for an underlying
- The user asks for a **Gamma Flip** price level
- The user wants a visual **HTML report** with GEX charts and metric cards
- The user asks about **market structure** for options trading

## Pipeline (4 Steps)

### Step 1: Fetch Market Data (Robinhood MCP)

Agent uses Robinhood MCP tools to fetch live data, then writes it as JSONs.

```text
get_equity_quotes(symbols=["TICKER"])          → stock_price
get_option_chains(underlying_symbol="TICKER")   → chain_id, expiration_dates
get_option_instruments(...)                     → option contracts (strike, type, id)
get_option_quotes(instrument_ids=[...])          → bid, ask, iv, delta, gamma, theta, vega
get_equity_historicals(...)                      → 90d OHLCV for historical_closes
```

Output: `scripts/sourced_data/<ticker>_0d.json`, `_30d.json`, and `_60d.json`

### Step 2: Patch OI/Volume (yfinance Fallback)

Run after writing JSONs to populate `open_interest` and `volume`.

```
C:\Python314\python.exe scripts\fetch_oi_volume.py
```

This auto-discovers all JSONs in `sourced_data/`, groups by ticker, fetches
option chains from yfinance, and patches `open_interest` / `volume` onto each
option entry. Also prints IV Rank, IV Percentile, and 52-week HV range.

> **Note:** `get_option_quotes` may already return `open_interest` and `volume`
> directly. If they are present in the JSON, skip this step. Run
> `fetch_oi_volume.py` only when quotes came back empty for those fields.

### Step 3: Calculate GEX

Reads the patched JSON and computes per-contract GEX + aggregate metrics.
Only uses `gamma` and `open_interest` from the input — never estimates.

```
C:\Python314\python.exe scripts\calculate_gex.py --market-data scripts/sourced_data/<ticker>_0d.json --output output/gex_<ticker>_0d.json
C:\Python314\python.exe scripts\calculate_gex.py --market-data scripts/sourced_data/<ticker>_30d.json --output output/gex_<ticker>_30d.json
C:\Python314\python.exe scripts\calculate_gex.py --market-data scripts/sourced_data/<ticker>_60d.json --output output/gex_<ticker>_60d.json
```

### Step 4: Generate HTML Report

Reads the GEX JSON(s) and renders a self-contained HTML page with metric cards,
regime badges, per-strike tables with bars, and a GEX profile chart. No data
fetching — purely formatting the already-computed JSON.

```
C:\Python314\python.exe scripts\gex_to_html.py --input output\gex_<ticker>_0d.json output\gex_<ticker>_30d.json output\gex_<ticker>_60d.json --label "0 DTE" "30 DTE" "60 DTE" --output output\gex_<ticker>.html
```

## Formula & Metrics

### Per-Contract GEX

```
GEX = gamma x open_interest x 100 x stock_price^2

Call GEX: +value  (dealers are long gamma → stabilizing)
Put GEX:  -value  (dealers are short gamma → amplifying)
```

### Aggregate Metrics

All metrics are **nullable** — they are `null` when no valid contracts exist.

| Metric | Nullable | Computation |
|--------|----------|-------------|
| **Net GEX** | Yes | Sum of all call GEX + all put GEX |
| **Absolute GEX** | Yes | Sum of \|GEX\| across all valid contracts |
| **GEX per 1%** | Yes | Net GEX × 0.01 (dollars dealers trade per 1% move) |
| **Total Call GEX** | Yes | Sum of all call GEX |
| **Total Put GEX** | Yes | Sum of all put GEX |
| **Call Wall** | Yes | Strike with the highest call GEX concentration |
| **Put Wall** | Yes | Strike with the highest (absolute) put GEX concentration |
| **Gamma Flip** | Yes | Interpolated strike where cumulative net GEX crosses zero |

### Gamma Flip Interpolation

Strikes are sorted ascending. Cumulative net GEX is summed from the lowest
strike upward. When the cumulative sum crosses zero, the flip level is
linearly interpolated between the straddling strikes:

```
fraction = -prev_cumulative / (cumulative - prev_cumulative)
gamma_flip = prev_strike + fraction x (strike - prev_strike)
```

Gamma Flip is `null` when:
- Fewer than 2 strikes have valid data
- Cumulative net GEX never crosses zero within the observed strike range
  (all strikes are on the same side of zero)

## GEX Interpretation

### Regimes

| Net GEX | Regime | Market Behavior | Favor |
|---------|--------|-----------------|-------|
| **Positive** | Stabilizing | Dealers buy dips, sell rallies. Range-bound, mean-reverting, compressed realized volatility. | Premium selling, theta strategies (covered calls, credit spreads, iron condors) |
| **Negative** | Amplifying | Dealers buy rallies, sell dips. Trending, explosive, expanded realized volatility. | Directional positioning, long premium (long calls/puts, straddles) |
| **Near zero** | Transition | Most dangerous zone. Market near Gamma Flip — a small move can flip the regime. | Defined-risk structures; reduce naked short premium |

### Key Levels

| Level | Meaning | How it acts |
|-------|---------|-------------|
| **Call Wall** | Strike with highest call GEX | Ceiling / resistance. Dealers sell into rallies as price approaches this level. Breakout above signals regime shift. |
| **Put Wall** | Strike with highest put GEX | Floor / support. Dealers buy into dips as price approaches this level. Breakdown below signals regime shift. |
| **Gamma Flip** | Strike where Net GEX crosses zero | Regime boundary. Above = stabilizing; below = amplifying. The most important single level. |

## Output Structure

### JSON Schema

When saved with `--output`, `calculate_gex.py` produces:

```json
{
  "generated_at": "2026-06-25T11:28:21",
  "ticker": "AVGO",
  "stock_price": 393.33,
  "expiration": "2026-07-24",
  "metrics": {
    "net_gex": 138563110.99,
    "net_gex_1pct": 1385631.10,
    "abs_gex": 622874941.33,
    "call_wall_strike": 420,
    "put_wall_strike": 370,
    "gamma_flip": 396.98,
    "total_call_gex": 380719026.16,
    "total_put_gex": -242155915.16
  },
  "regime": "POSITIVE GEX — Stabilizing. Dealers buy dips, sell rallies.",
  "strikes": [
    {
      "strike": 370.0,
      "call_gex": 34614477.31,
      "put_gex": -37427077.63,
      "net_gex": -2812600.33,
      "pct_of_abs": 0.45
    }
  ],
  "data_quality": {
    "total_options": 22,
    "valid_options": 22,
    "skipped_no_gamma": 0,
    "skipped_no_oi": 0
  }
}
```

When `gamma_flip` or any metric is N/A, it is stored as `null`.

### HTML Report Layout

Generated by `gex_to_html.py`. A self-contained page (all CSS inline) with:

1. **Header** — ticker, stock price, expiration, DTE, generation timestamp
2. **Regime Badge** — color-coded: green (positive), red (negative), amber (mixed/transition)
3. **Metric Cards** — 7 cards in a responsive grid: Net GEX, Abs GEX, Total Call/Put GEX, Call Wall, Put Wall, Gamma Flip
4. **Strike Profile Table** — per-strike rows with inline bar visualizations (blue = call GEX, red = put GEX) + Net GEX + %Abs
5. **GEX Profile Chart** — horizontal stacked bars showing call vs put GEX at each strike
6. **Data Quality Note** — valid/total contracts, any reasons for skipping
7. **Footer** — methodology reference

When combined for multiple expiries (e.g., 0 DTE + 30 DTE + 60 DTE), each expiry appears
as a separate section within the same HTML page.

## CLI Reference

### calculate_gex.py

```
usage: calculate_gex.py [-h] --market-data MARKET_DATA
                        [--stock-price STOCK_PRICE]
                        [--output OUTPUT] [--ticker TICKER]

GEX (Gamma Exposure) Calculator — SpotGamma methodology.

options:
  -h, --help            show this help message and exit
  --market-data MARKET_DATA
                        Path to JSON with stock_price + options[].
                        Each option needs: strike, type, gamma, open_interest.
  --stock-price STOCK_PRICE
                        Override stock price from JSON.
  --output OUTPUT       Save GEX results as JSON.
  --ticker TICKER       Override ticker symbol in report header.
```

### gex_to_html.py

```
usage: gex_to_html.py [-h] --input INPUT [INPUT ...]
                      [--output OUTPUT] [--label [LABEL ...]]

Generate an HTML report from GEX JSON data.

options:
  -h, --help            show this help message and exit
  --input, -i           One or more GEX JSON files to include in the report.
  --output, -o          Output HTML file path. Defaults to <input_stem>.html
                        for single files, output/gex_combined.html for multiple.
  --label, -l           Labels for each input (e.g. --label '0 DTE' '30 DTE' '60 DTE').
```

## Data Quality Tracking

Every metric computation tracks how many contracts were used and why any were
skipped. This is reported both in the terminal output and the JSON.

```text
Valid Contracts:       22 / 22 options
```
or
```text
Valid Contracts:       31 / 38 options
Skipped (no OI):       7
```

The `data_quality` section in the JSON always contains:
| Field | Meaning |
|-------|---------|
| `total_options` | Size of the input options array |
| `valid_options` | Contracts with both gamma > 0 and OI > 0 |
| `skipped_no_gamma` | Contracts skipped because gamma was missing, zero, or null |
| `skipped_no_oi` | Contracts skipped because OI was missing, zero, or null |

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| All metrics show N/A | No valid contracts found | Check `data_quality` for skip counts. Run `fetch_oi_volume.py` to patch OI. |
| Gamma Flip is N/A | < 2 strikes with data, or cumulative never crosses zero | This is valid — the options chain may be entirely bullish or bearish with no regime flip. Report it as-is. |
| Only some strikes have data | Those are the only contracts with both gamma and OI | That's expected behavior. Data quality shows the exact counts. |
| GEX seems small | Small stock price, low OI, or low gamma | GEX scales with price squared, OI, and gamma. Low values are valid. |
| Script errors: "no valid stock_price" | JSON missing stock_price and no `--stock-price` | Provide `--stock-price` or ensure `stock_price` field exists in the JSON. |
| HTML report empty sections | Corresponding JSON had N/A metrics | The HTML handles null data gracefully — sections show "N/A" metrics. |

## Workflow Integration

This skill integrates into the **Options Strategy Advisor** workflow as steps
9.5 (calculate_gex.py) and 9.75 (gex_to_html.py), placed between the OI/volume
fetch (step 9) and Black-Scholes analysis (step 10). The GEX metrics feed into
the **Gamma Exposure Profile** section of the combined term structure report.

See `AGENTS.md` for the full ticker analysis workflow and `SKILL.md` in the
`options-strategy-advisor` skill directory for the broader option analysis flow.
