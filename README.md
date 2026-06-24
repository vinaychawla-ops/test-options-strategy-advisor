# Options Strategy Advisor

Educational options trading tool providing theoretical pricing, strategy analysis, and risk management guidance using Black-Scholes model.

## Overview

Options Strategy Advisor helps traders understand and analyze options strategies without requiring expensive real-time options data. It uses theoretical pricing models (Black-Scholes) combined with live market data sourced via the **Robinhood MCP server** (stock quotes, option chains, IV, Greeks), **Yahoo Finance (yfinance)** fallback for OI/Volume, and FMP API (historical volatility, dividends).

**Key Features:**
- ✅ Black-Scholes pricing engine
- ✅ All Greeks calculation (Delta, Gamma, Theta, Vega, Rho)
- ✅ Live option data via Robinhood MCP (bid/ask, IV, market Greeks)
- ✅ 17+ options strategies supported
- ✅ P/L simulation and visualization
- ✅ Earnings strategy integration
- ✅ Historical volatility calculation
- ✅ Realized volatility vs IV comparison (Robinhood MCP primary, Barchart validation)
- ✅ Expected Move (1SD) calculation
- ✅ Lognormal probability estimates (assigns numeric probabilities to key strike levels)
- ✅ RV Regime Analysis (10/20/30/60 day windows with acceleration/plateau trend)
- ✅ Open Interest & Volume analysis (yfinance fallback)
- ✅ IV Rank & IV Percentile (rolling 30d HV distribution vs yfinance)
- ✅ Risk management guidance
- ✅ At-Expiry Payoff tables (Trade Ideas section, both expirations)

## Why This Approach?

**No expensive data subscriptions needed:**
- Real-time options data: $99-$500/month (Polygon.io, Intrinio)
- Robinhood MCP: Free (agent-fetched data)
- FMP API Free tier: $0/month (250 requests/day)

**Educational focus:**
- Learn how strategies work
- Understand Greeks and risk metrics
- Compare strategies side-by-side

**Practical application:**
- Theoretical prices ≈ market mid-prices
- Compare BS theoretical price vs actual market bid/ask
- Good for strategy planning and education

## Supported Strategies

### Income Strategies
1. **Covered Call** - Generate income from stock holdings
2. **Cash-Secured Put** - Get paid to buy stock
3. **Poor Man's Covered Call** - Capital-efficient covered call

### Protection Strategies
4. **Protective Put** - Insurance for stock positions
5. **Collar** - Limited risk/reward protection

### Directional Strategies
6. **Bull Call Spread** - Limited risk bullish play
7. **Bull Put Spread** - Credit spread for bullish view
8. **Bear Call Spread** - Credit spread for bearish view
9. **Bear Put Spread** - Limited risk bearish play

### Volatility Strategies
10. **Long Straddle** - Profit from big moves
11. **Long Strangle** - Cheaper straddle, bigger move needed
12. **Short Straddle** - Profit from no movement (high risk)
13. **Short Strangle** - Wider range straddle

### Range-Bound Strategies
14. **Iron Condor** - Profit from range-bound trading
15. **Iron Butterfly** - Tight range profit

### Advanced Strategies
16. **Calendar Spread** - Time decay play
17. **Diagonal Spread** - Directional + time decay

## Installation

### Prerequisites
- Python 3.8+
- **Robinhood MCP server** — configured in agent environment for live stock & options data
- FMP API key (for historical volatility and dividend yield — free tier sufficient)

### Install Dependencies
```bash
pip install numpy scipy requests pandas yfinance
```

### Get FMP API Key
1. Visit https://financialmodelingprep.com/developer/docs
2. Sign up for free account
3. Copy API key
4. Set environment variable:
```bash
export FMP_API_KEY="your_key_here"
```

## Quick Start

### Test Black-Scholes Pricer

```bash
# Default example (AAPL-like defaults)
python scripts/black_scholes.py

# With live market data from Robinhood MCP (agent prepares JSON)
python scripts/black_scholes.py --market-data scripts/sourced_data/bmnr_data.json --strike 16 --days 2

# With realized volatility comparison (requires historical_closes in JSON)
python scripts/black_scholes.py --market-data scripts/sourced_data/avgo_30d.json --strike 395 --days 32 --realized-vol

# With inline close prices for realized vol
python scripts/black_scholes.py --stock-price 393 --strike 395 --days 30 --volatility 0.48 --realized-vol --closes 318.29 318.81 309.41 300.68 293.41 309.51 313.49
```

**Example Output (default run):**
```
BLACK-SCHOLES OPTIONS PRICER - EXAMPLE
======================================================================

Input Parameters:
  Stock Price: $180.00
  Strike Price: $185.00
  Days to Expiration: 30
  Volatility: 25.0%
  Risk-Free Rate: 5.30%
  Dividend Yield: 1.0%

======================================================================
CALL OPTION
======================================================================
Price: $2.45
Intrinsic Value: $0.00
Time Value: $2.45

Greeks:
  Delta: 0.3654 ($36.54 per $1 move)
  Gamma: 0.0234 (delta changes by 0.0234)
  Theta: -$0.18/day (loses $0.18 per day)
  Vega: $0.25 per 1% IV (gains $0.25 if IV +1%)
  Rho: $0.12 per 1% rate (gains $0.12 if rate +1%)
```

### Use in Your Code

```python
from scripts.black_scholes import OptionPricer

# Initialize pricer
pricer = OptionPricer(
    S=180,          # Stock price
    K=185,          # Strike price
    T=30/365,       # Time to expiration (years)
    r=0.053,        # Risk-free rate (5.3%)
    sigma=0.25,     # Volatility (25%)
    q=0.01          # Dividend yield (1%)
)

# Get call option price
call_price = pricer.call_price()
print(f"Call Price: ${call_price:.2f}")

# Get all Greeks for call
call_greeks = pricer.get_all_greeks('call')
print(f"Delta: {call_greeks['delta']:.4f}")
print(f"Gamma: {call_greeks['gamma']:.4f}")
print(f"Theta: ${call_greeks['theta']:.2f}/day")
print(f"Vega: ${call_greeks['vega']:.2f} per 1%")
```

### Calculate Historical Volatility

```python
from scripts.black_scholes import (
    calculate_historical_volatility,
    fetch_historical_prices_for_hv
)

# Fetch prices from FMP
api_key = "your_key"
prices = fetch_historical_prices_for_hv("AAPL", api_key, days=90)

# Calculate 30-day HV
hv = calculate_historical_volatility(prices, window=30)
print(f"30-Day HV: {hv*100:.2f}%")
```

## Understanding the Metrics

### Option Price Components

**Intrinsic Value:**
- Call: max(0, Stock Price - Strike Price)
- Put: max(0, Strike Price - Stock Price)

**Time Value:**
- Option Price - Intrinsic Value
- Decays to $0 at expiration

### The Greeks

**Delta (Δ)** - Directional Exposure
```
Range: 0 to 1 (calls), -1 to 0 (puts)
Meaning: Change in option price per $1 stock move

Example: Δ = 0.50
→ If stock +$1, option +$0.50
→ If stock -$1, option -$0.50
```

**Gamma (Γ)** - Delta Acceleration
```
Meaning: Change in delta per $1 stock move
Peak: ATM options
Low: Deep ITM or OTM

Example: Γ = 0.05, Δ currently = 0.50
→ If stock +$1, delta becomes 0.55
```

**Theta (Θ)** - Time Decay
```
Meaning: Change in option price per day
Sign: Usually negative (options lose value over time)
Peak: Last 30 days before expiration

Example: Θ = -$0.15/day
→ Tomorrow, option loses $0.15 if nothing else changes
```

**Vega (ν)** - Volatility Sensitivity
```
Meaning: Change in option price per 1% IV change
Sign: Always positive (options gain value when vol increases)

Example: ν = $0.25 per 1%
→ If IV increases from 25% to 26%, option +$0.25
```

**Rho (ρ)** - Interest Rate Sensitivity
```
Meaning: Change in option price per 1% rate change
Sign: Positive for calls, negative for puts
Impact: Usually small unless long-dated options

Example: ρ = $0.10 per 1%
→ If interest rate increases 1%, option +$0.10
```

### Expected Move (1SD)

The expected move estimates the range the stock will stay within ~68% of the time:

```
Expected Move = Stock Price × IV × √(DTE / 365)
```

**Example (AVGO 32 DTE):** $393 × 0.48 × √(32/365) ≈ **$56** → 68% confidence range of **$337–$449**

All trade ideas should be evaluated against this range. A breakeven inside the range is more achievable; one outside demands a rare move.

### Lognormal Probability Estimates

For any strike price K, the probability of the stock finishing above/below that strike is:

```
z = ln(K / S) / (σ√T)
P(below K) = N(z)    // standard normal CDF
P(above K) = 1 - N(z)
```

**Example (AVGO 32 DTE, $370 strike):** z = ln(370/393) / (0.473 × √(32/365)) = -0.44 → **~33% chance of finishing below $370**

These IV-derived probabilities reflect market pricing, not a forecast. They are most useful for comparing assignment risk across strikes.

### At-Expiry Payoff Tables

The Trade Ideas section includes a payoff table for each expiration summarizing how each recommended strategy performs at four stock price levels at expiry:

| AVGO at Expiry | Straddle | Bull Call | Bear Put | Short Put |
| -------------- | :------: | :-------: | :------: | :-------: |
| $350 (deep down) | Gain | Lose | Max Gain | Assigned |
| $390 (near down) | Lose | Lose | Partial Gain | Keep Premium |
| $400 (near up) | Lose | Partial Gain | Lose | Keep Premium |
| $450 (deep up) | Gain | Max Gain | Lose | Keep Premium |

**Payoff labels:** Gain, Lose, Max Gain, Max Loss, Partial Gain, Assigned (short put assigned), Keep Premium (short put expired worthless).

### Volatility: HV vs IV

**Historical Volatility (HV) / Realized Volatility (RV):**
- Calculated from past price movements
- Objective, based on actual data
- Available free (from Robinhood MCP historical data or FMP)

**Implied Volatility (IV):**
- Derived from option market prices
- Subjective, based on supply/demand
- Requires real-time options data (Robinhood MCP)

**Comparison:**
```
IV > HV: Options expensive → Consider selling premium
IV < HV: Options cheap → Consider buying options
IV = HV: Fairly priced → Any strategy works
```

**Realized Volatility Report (via `--realized-vol`):**

When run with `--market-data` containing a `historical_closes` array, or with `--closes`, the script computes RV-10/20/30/60 and compares each to current IV with neutral labels (RV > IV / RV ~ IV / RV < IV):

```
Realized Volatility (from historical closes):
----------------------------------------------------------------------
  Period           RV      IV/RV
  --------     ------   --------
  RV-10        68.4%     0.69x  (RV > IV)
  RV-20        73.1%     0.65x  (RV > IV)
  RV-30        65.1%     0.73x  (RV > IV)
  RV-60        55.2%     0.86x  (RV > IV)
  RV-Long      55.2%     0.86x  (RV > IV)

  Current IV (input): 47.4%
  Data points: 61 closes, 60 daily returns
```

The label `(RV > IV)` means realized vol exceeds implied vol — not "cheap". Whether options are cheap depends on whether RV mean-reverts or persists. See the report's Vol Thesis Conflict callout for guidance.

## Common Workflows

### 1. Analyze a Strategy

```python
from scripts.black_scholes import OptionPricer

# Stock: AAPL @ $180
# Strategy: Bull Call Spread $180/$185 (30 DTE)

# Price long call ($180 strike)
long_call = OptionPricer(S=180, K=180, T=30/365, r=0.053, sigma=0.25)
long_price = long_call.call_price()
long_delta = long_call.call_delta()

# Price short call ($185 strike)
short_call = OptionPricer(S=180, K=185, T=30/365, r=0.053, sigma=0.25)
short_price = short_call.call_price()
short_delta = short_call.call_delta()

# Strategy metrics
net_debit = long_price - short_price
max_profit = (185 - 180) - net_debit
max_loss = -net_debit
position_delta = long_delta - short_delta

print(f"Bull Call Spread $180/$185")
print(f"Net Debit: ${net_debit:.2f}")
print(f"Max Profit: ${max_profit:.2f} (at $185+)")
print(f"Max Loss: ${max_loss:.2f} (at $180-)")
print(f"Position Delta: {position_delta:.4f}")
```

### 2. Compare IV to HV

```python
# Get HV via FMP
prices = fetch_historical_prices_for_hv("AAPL", api_key, days=90)
hv = calculate_historical_volatility(prices, window=30)

# User provides IV (from broker platform)
iv = 0.28  # 28% from ThinkorSwim

print(f"Historical Volatility: {hv*100:.2f}%")
print(f"Implied Volatility: {iv*100:.1f}%")

if iv > hv * 1.1:
    print("→ Options expensive (IV > HV) - Consider selling premium")
elif iv < hv * 0.9:
    print("→ Options cheap (IV < HV) - Consider buying options")
else:
    print("→ Fairly priced")
```

### 2b. Realized Vol Comparison (Robinhood MCP Data)

```bash
# Agent prepares JSON with historical_closes array
python scripts/black_scholes.py \
  --market-data scripts/sourced_data/avgo_30d.json \
  --strike 395 --days 32 \
  --realized-vol
```

The `historical_closes` array in the market data JSON is populated by the agent from `get_equity_historicals()` via Robinhood MCP. The script computes RV-10/20/30/60 and labels each with neutral direction (RV > IV / RV ~ IV / RV < IV). The interpretive "cheap vs expensive" judgment belongs in the report, not in the tool output.

### 3. Earnings Strategy

Check if earnings coming up (use Earnings Calendar skill):
```python
# If earnings in 7 days:
# - IV typically elevated (30-50% higher)
# - Consider straddle/strangle (profit from big move)
# - Or sell iron condor (profit from IV crush)

# Example: Long Straddle
straddle_cost = call_price + put_price
breakeven_up = stock_price + straddle_cost
breakeven_down = stock_price - straddle_cost

print(f"Straddle Cost: ${straddle_cost:.2f}")
print(f"Breakevens: ${breakeven_down:.2f} / ${breakeven_up:.2f}")
print(f"Need {abs(breakeven_up - stock_price)/stock_price*100:.1f}% move to profit")
```

## Limitations & Best Practices

### Theoretical vs Market Prices

**Black-Scholes Assumptions:**
- European options (can't exercise early)
- Constant volatility (changes in reality)
- No transaction costs
- Continuous trading

**Real World Differences:**
- American options (most stocks) can exercise early
- Bid-ask spread: Actual cost higher than theoretical mid
- Commissions and slippage
- Liquidity: Wide markets on illiquid options

### Best Practices

**1. Use for Education & Planning:**
- Learn how strategies work
- Compare different approaches
- Understand risk/reward before trading

**2. Verify Before Trading:**
- Get real quotes from your broker
- Check bid-ask spread
- Confirm option liquidity (open interest, volume)

**3. Input Actual IV:**
- Theoretical price assumes constant volatility
- Use current market IV for accuracy
- Check IV percentile (high/low relative to history)

**4. Account for Dividends:**
- Ex-dividend dates affect option prices
- Calls lose value, puts gain value on ex-div date
- Script supports dividend yield input

**5. Monitor Greeks:**
- Delta: Overall directional exposure
- Theta: Daily time decay (seller advantage)
- Vega: Volatility risk (watch during earnings)
- Gamma: Risk of delta changing (avoid near expiration)

## Integration with Other Skills

**Earnings Calendar:**
- Fetch earnings dates
- Identify IV crush opportunities
- Time earnings strategies

**Technical Analyst:**
- Use support/resistance for strike selection
- Trend analysis for directional strategies
- Breakout potential for straddle timing

**US Stock Analysis:**
- Fundamental analysis for LEAPS
- Dividend yield for covered call/put
- Earnings quality for earnings plays

**Bubble Detector:**
- High risk → protective puts
- Low risk → bullish strategies
- Critical risk → avoid long premium

**Portfolio Manager:**
- Track options with stock positions
- Aggregate Greeks across portfolio
- Options as hedging tool

## API Usage & Costs

**Free Tier Sufficient:**
- Stock prices: 1 request per symbol
- Historical prices (HV): 1 request per symbol
- Dividend data: 1 request per symbol

**Example Analysis Cost:**
```
Covered Call on AAPL:
- Current price: 1 request
- HV calculation: 1 request (90 days data)
- Dividend yield: 1 request
Total: 3 requests

Daily budget: 250 requests / day
→ Can analyze ~80 strategies per day
```

## Troubleshooting

### Negative Option Price
**Cause:** Invalid inputs (strike vs stock price)
**Solution:** Check that inputs make sense

### Greeks Seem Wrong
**Cause:** Using wrong units (annual vs daily)
**Solution:** Verify T is in years, theta is per day

### HV Very Different from IV
**Normal:** IV reflects future expectations, HV is past
**Action:** Use IV from broker for more accuracy

### Option Price Too High/Low
**Cause:** Volatility input incorrect
**Solution:** Verify sigma is annual (e.g., 0.25 for 25%)

## Resources

### Project Files
- `SKILL.md` - Complete workflow and strategies
- `scripts/black_scholes.py` - Black-Scholes pricing engine & Greeks
- `scripts/fetch_oi_volume.py` - yfinance fallback for OI/Volume in JSONs
- `scripts/sourced_data/` - Agent-prepared market data JSON files (Robinhood MCP)
- `output/` - Final analysis reports in Markdown (`<stock>_options_<strategy>_<YYYYMMDD_HHmmss>.md`)
- `references/` - Methodology and strategy reference docs

### Data Flow
1. Agent fetches live stock & option data from **Robinhood MCP** server
2. Data is saved as JSON under `scripts/sourced_data/<ticker>.json`
3. Script reads it via `--market-data <path>` flag
4. Agent also fetches 90 days of OHLCV via `get_equity_historicals()` and includes close prices as `historical_closes` array in the JSON
5. Run `scripts/fetch_oi_volume.py` to populate `open_interest` and `volume` fields via yfinance fallback (when Robinhood quotes return empty)
6. Run with `--realized-vol` to get RV-10/20/30/60 comparisons against current IV (labels: RV > IV / RV ~ IV / RV < IV)
7. Report includes 13 sections: Summary, Volatility Context (IV/RV, RV Regime, IV Profile), Expected Move (1SD), Probability Estimates (lognormal), IV Skew (both expirations), Greeks Comparison, BS Validation, Vol Term Structure, Time Decay, Trade Ideas (with At-Expiry Payoff tables for both expirations), Risk Metrics, Day-over-Day Context, Open Interest & Volume Analysis
8. Alternatively, use `--ticker` + FMP API for stock price + HV

### External Resources
- Options Playbook: https://www.optionsplaybook.com/
- CBOE Education: https://www.cboe.com/education/
- Black-Scholes Calculator: https://www.option-price.com/

## Future Enhancements

**Planned:**
- Strategy simulation script (complete P/L analysis)
- P/L diagram generator (ASCII art)
- Earnings strategy advisor (integrated with Earnings Calendar)
- Complete strategy reference guides

**Contributions Welcome:**
- Additional strategies
- Improved volatility models
- Better visualization tools

## License

Educational use. Trade at your own risk. Options involve significant risk and are not suitable for all investors.

---

**Version:** 1.5
**Last Updated:** 2026-06-23
**Dependencies:** Python 3.8+, numpy, scipy, requests, yfinance
**Live Data:** Robinhood MCP server (primary) | yfinance (fallback for OI/Volume) | FMP API (fallback for HV & dividends)
**Model:** Black-Scholes (European options pricing)
