# Options Strategy Advisor — Agent Guide

## Project Overview

Black-Scholes options pricing engine with live market data sourced via Robinhood MCP. Compares theoretical prices against real market bid/ask/IV/Greeks.

## Data Source Priority

1. **Robinhood MCP** — Agent fetches live stock quotes, option chains, instruments, and quotes
2. **`--market-data <json>`** — Python script reads agent-prepared JSON from `scripts/sourced_data/`
3. **Yahoo Finance (yfinance)** — Fallback for Open Interest, Volume, IV Rank, and IV Percentile when `get_option_quotes` returns empty; run `scripts/fetch_oi_volume.py` after writing JSONs (auto-discovers all JSONs in `sourced_data/`, groups by ticker, caches Ticker objects)
4. **FMP API** — Fallback for historical volatility and dividend yield (requires `FMP_API_KEY` env var)
5. **Manual CLI flags** — `--stock-price`, `--iv`, `--strike`, `--days` override everything

## Directory Structure

```
scripts/
  black_scholes.py       # Pricing engine and Greeks
  calculate_gex.py       # Gamma Exposure (GEX) calculator
  fetch_oi_volume.py     # yfinance fallback for OI/volume in JSONs
  sourced_data/           # Agent-prepared market data JSONs
  tests/                  # Pytest test suite (51 tests)
    conftest.py
    test_black_scholes.py
    test_fmp_endpoints.py
    test_fetch_oi_volume.py
output/                   # Analysis reports (Markdown)
references/               # Methodology docs
AGENT.md                  # This file
SKILL.md                  # Full analysis workflow
```

## Workflow for Any New Ticker

1. Fetch stock quote: `get_equity_quotes(symbols=["TICKER"])`
2. Fetch option chain: `get_option_chains(underlying_symbol="TICKER")`
3. Pick ~30 DTE and ~60 DTE monthly expirations from `expiration_dates`
4. Fetch instruments for ATM±5 strikes (calls + puts) for each expiry
5. Fetch quotes: `get_option_quotes(instrument_ids=[...])`
6. Write JSONs to `scripts/sourced_data/<ticker>_30d.json` and `_60d.json`
7. Fetch 90 days of OHLCV data: `get_equity_historicals(symbols=["TICKER"], interval="day", start_time="...", end_time="...")`
8. Include `"historical_closes"` array in both market data JSONs (chronological close prices from step 7)
9. Fetch OI/volume via yfinance fallback (run after writing JSONs, in case Robinhood quotes returned empty):
   ```
   C:\Python314\python.exe scripts\fetch_oi_volume.py
   ```
   This auto-discovers all JSONs in `sourced_data/`, reads `ticker`/`expiration` from each, groups by ticker for Ticker-caching efficiency, patches OI/volume, and prints IV Rank/Percentile for each underlying.
9.5. Run GEX analysis for both expirations:
   ```
   C:\Python314\python.exe scripts\calculate_gex.py --market-data scripts/sourced_data/<ticker>_30d.json --output output/gex_<ticker>_30d.json
   C:\Python314\python.exe scripts\calculate_gex.py --market-data scripts/sourced_data/<ticker>_60d.json --output output/gex_<ticker>_60d.json
   ```
   Computes Net GEX, Absolute GEX, Call Wall, Put Wall, Gamma Flip, and per-strike GEX profile. Only uses gamma + open_interest from fetched data — no estimation. If gamma or OI is missing, that contract is skipped and noted in data_quality.
9.75. Generate HTML report from GEX JSONs:
   ```
   C:\Python314\python.exe scripts\gex_to_html.py --input output\gex_<ticker>_30d.json output\gex_<ticker>_60d.json --output output\gex_<ticker>.html
   ```
   Self-contained HTML page with color-coded regime badges, metric cards, and per-strike bar charts. No data fetching — pure formatting from saved JSONs.
10. Run BS for each with `--realized-vol`:
   ```
   C:\Python314\python.exe scripts\black_scholes.py --market-data scripts/sourced_data/<ticker>_30d.json --strike <ATM> --days 30 --realized-vol
   C:\Python314\python.exe scripts\black_scholes.py --market-data scripts/sourced_data/<ticker>_60d.json --strike <ATM> --days 66 --realized-vol
   ```
11. Compile combined report to `output/<ticker>_options_termstructure_<YYYYMMDD_HHmmss>.md`. Report must include:
    - **Volatility Context**: IV vs RV comparison, RV Regime Analysis (10/20/30/60d), IV Profile (Rank/Percentile)
    - **Expected Move (1SD)**: stock × IV × √(DTE/365) — table for both expirations
    - **Probability Estimates**: Lognormal-derived probabilities (`z = ln(K/S) / (σ√T)`) for key levels
    - **Vol Thesis Conflict**: Callout explaining that IV < RV favors long premium but directional bias may favor short premium — competing signals
    - **Open Interest & Volume Analysis**: Per-strike tables with OI, volume, PC Vol Ratio, PC OI Ratio for both expirations (source: yfinance fallback)
    - **Gamma Exposure Profile**: Net GEX, Abs GEX, Call Wall, Put Wall, Gamma Flip, regime callout, and per-strike GEX breakdown from `calculate_gex.py`
    - **Skew Interpretation**: Do NOT infer call buying from IV alone — mention "may reflect call demand, reduced put demand, dealer positioning, or data artifacts"
    - **BS Validation**: For large discrepancies, say "unresolved pricing discrepancy requiring further validation" rather than "put-call parity breakdown"
    - **Trade Ideas**: Each idea annotated with probability of profit/assignment and expected move context; must include **At-Expiry Payoff** table for both expirations (rows = 4 price levels, cols = the 4 strategies) using labels: Gain/Lose/Max Gain/Max Loss/Partial Gain/Assigned/Keep Premium

## Key CLI Flags

| Flag | Description |
|------|-------------|
| `--market-data <path>` | Load JSON with stock_price + options array (bid, ask, iv, delta, gamma, theta, vega) |
| `--stock-price <float>` | Override stock price |
| `--strike <float>` | Strike price (default: 185) |
| `--days <int>` | Days to expiration (default: 30) |
| `--volatility <float>` | Volatility as decimal (default: 0.25) |
| `--iv <float>` | Implied volatility (overrides --volatility) |
| `--option-type <call\|put\|both>` | Option type (default: both) |
| `--ticker <str>` | Stock symbol (for FMP fallback) |
| `--risk-free-rate <float>` | Risk-free rate (default: 0.053) |
| `--dividend-yield <float>` | Dividend yield (default: 0.01) |
| `--output <path>` | Save GEX results as JSON (used with `calculate_gex.py`) |
| `--realized-vol` | Compute RV-10/20/30/60 from `historical_closes` in JSON (or `--closes`) |
| `--closes <floats...>` | Chronological close prices for realized vol (space-separated) |

## Running Commands

**Python executable:** Always use `C:\Python314\python.exe` (has numpy/scipy installed)

```
C:\Python314\python.exe scripts\black_scholes.py --help
C:\Python314\python.exe scripts\black_scholes.py --market-data scripts\sourced_data\file.json --strike 16 --days 30
```

**OI/Volume fallback (run after writing JSONs):**
```
C:\Python314\python.exe scripts\fetch_oi_volume.py
```

**GEX Analysis (run after OI/volume patch):**
```
C:\Python314\python.exe scripts\calculate_gex.py --market-data scripts/sourced_data/file.json --output output/gex_file.json
```

**HTML Report (run after GEX analysis):**
```
C:\Python314\python.exe scripts\gex_to_html.py --input output\gex_file.json output\gex_file2.json --output output\gex_report.html
```

**Tests:**
```
C:\Python314\python.exe -m pytest scripts\tests\ -v
```

## Naming Conventions

- Market data JSONs: `scripts/sourced_data/<ticker>_<dte>d.json`
- Output reports: `output/<ticker>_options_<strategy>_<YYYYMMDD_HHmmss>.md`
- Datetime format: 24-hour, e.g. `20260616_150944`

## Rules

- **No real trading** — theoretical/educational only
- **No commits without explicit user request**
- **No API keys or secrets in AGENT.md** — env vars only
- **Always run `C:\Python314\python.exe`** — don't use system python
- **After any edit, run tests** to verify nothing broke
- **Store market data JSONs in `scripts/sourced_data/`** — never in root or elsewhere
- **Always run `scripts/fetch_oi_volume.py` after writing JSONs** — populates `volume` and `open_interest` fields via yfinance fallback
- **Always run `scripts/calculate_gex.py` after OI/volume patch** — computes Net GEX, Call Wall, Put Wall, Gamma Flip, and per-strike GEX profile
- **Never estimate data** — every number in a report must come from a fetched source, a computed derivation (BS model, RV, IV stats), or a BS model run. Do not fill gaps with guesses. If a strike lacks a market quote, either fetch it or note it as unavailable.

## Reference

Full analysis workflow (strategy types, Greeks, P/L diagrams, output templates) is documented in `SKILL.md`.
