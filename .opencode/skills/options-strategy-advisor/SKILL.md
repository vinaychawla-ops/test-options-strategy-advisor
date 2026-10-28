---
name: options-strategy-advisor
description: Options trading strategy analysis and simulation tool. Provides theoretical pricing using Black-Scholes model, Greeks calculation, strategy P/L simulation, and risk management guidance. Use when user requests options strategy analysis, covered calls, protective puts, spreads, iron condors, earnings plays, or options risk management. Includes volatility analysis, position sizing, and earnings-based strategy recommendations. Educational focus with practical trade simulation.
---

# Options Strategy Advisor

## Overview

This skill provides comprehensive options strategy analysis and education using theoretical pricing models. It helps traders understand, analyze, and simulate options strategies without requiring real-time market data subscriptions.

**Core Capabilities:**
- **Black-Scholes Pricing**: Theoretical option prices and Greeks calculation
- **Strategy Simulation**: P/L analysis for major options strategies
- **Earnings Strategies**: Pre-earnings volatility plays integrated with Earnings Calendar
- **Risk Management**: Position sizing, Greeks exposure, max loss/profit analysis
- **Educational Focus**: Detailed explanations of strategies and risk metrics

**Data Sources (priority order):**
1. **Robinhood MCP server** (primary live data): Stock prices, option chains, option quotes with IV & Greeks. Agent fetches and writes to `scripts/sourced_data/<ticker>_<expiry>.json`.
2. **Yahoo Finance (yfinance)** — OI/Volume and IV Rank/Percentile fallback. Run `scripts/fetch_oi_volume.py` after writing JSONs to patch OI/volume and compute IV stats from rolling 30d HV.
3. **FMP API** (fallback): Historical volatility, dividend yield, earnings dates. Also stock price when Robinhood MCP is unavailable.
4. **`--market-data <file>` flag**: The Python script reads a JSON file prepared by the agent from Robinhood MCP data (saved under `scripts/sourced_data/`).
5. **User Input**: Manual stock price, IV, strike, days, risk-free rate overrides.
6. **Theoretical Models**: Black-Scholes for pricing and Greeks.

## Prerequisites

**Required:**
- Python 3.8+ with `numpy`, `scipy`, `requests`
- **Robinhood MCP server** (for live stock & options data) — configured in the agent environment

**Optional:**
- FMP API key (for historical volatility and dividend yield)
  - Set via `FMP_API_KEY` environment variable or `--api-key` argument
  - Without API key: Use manual inputs for stock price and volatility

**Installation:**
```bash
pip install numpy scipy requests yfinance pandas
```

**Quick Start Examples:**
```bash
# Basic call option pricing (no API key needed)
python3 scripts/black_scholes.py

# With Robinhood-sourced market data (JSON prepared by agent)
python3 scripts/black_scholes.py --market-data scripts/sourced_data/bmnr_data.json

# With FMP API key for real-time data
python3 scripts/black_scholes.py --ticker AAPL --api-key $FMP_API_KEY

# Custom option parameters
python3 scripts/black_scholes.py --stock-price 180 --strike 185 --days 30 --volatility 0.25

# Put option analysis
python3 scripts/black_scholes.py --stock-price 180 --strike 175 --days 30 --option-type put
```

## When to Use This Skill

Use this skill when:
- User asks about options strategies ("What's a covered call?", "How does an iron condor work?")
- User wants to simulate strategy P/L ("What's my max profit on a bull call spread?")
- User needs Greeks analysis ("What's my delta exposure?")
- User asks about earnings strategies ("Should I buy a straddle before earnings?")
- User wants to compare strategies ("Covered call vs protective put?")
- User needs position sizing guidance ("How many contracts should I trade?")
- User asks about volatility ("Is IV high right now?")

Example requests:
- "Analyze a covered call on AAPL"
- "What's the P/L on a $100/$105 bull call spread on MSFT?"
- "Should I trade a straddle before NVDA earnings?"
- "Calculate Greeks for my iron condor position"
- "Compare protective put vs covered call for downside protection"

## Supported Strategies

### Income Strategies
1. **Covered Call** - Own stock, sell call (generate income, cap upside)
2. **Cash-Secured Put** - Sell put with cash backing (collect premium, willing to buy stock)
3. **Poor Man's Covered Call** - LEAPS call + short near-term call (capital efficient)

### Protection Strategies
4. **Protective Put** - Own stock, buy put (insurance, limited downside)
5. **Collar** - Own stock, sell call + buy put (limited upside/downside)

### Directional Strategies
6. **Bull Call Spread** - Buy lower strike call, sell higher strike call (limited risk/reward bullish)
7. **Bull Put Spread** - Sell higher strike put, buy lower strike put (credit spread, bullish)
8. **Bear Call Spread** - Sell lower strike call, buy higher strike call (credit spread, bearish)
9. **Bear Put Spread** - Buy higher strike put, sell lower strike put (limited risk/reward bearish)

### Volatility Strategies
10. **Long Straddle** - Buy ATM call + ATM put (profit from big move either direction)
11. **Long Strangle** - Buy OTM call + OTM put (cheaper than straddle, bigger move needed)
12. **Short Straddle** - Sell ATM call + ATM put (profit from no movement, unlimited risk)
13. **Short Strangle** - Sell OTM call + OTM put (profit from no movement, wider range)

### Range-Bound Strategies
14. **Iron Condor** - Bull put spread + bear call spread (profit from range-bound movement)
15. **Iron Butterfly** - Sell ATM straddle, buy OTM strangle (profit from tight range)

### Advanced Strategies
16. **Calendar Spread** - Sell near-term option, buy longer-term option (profit from time decay)
17. **Diagonal Spread** - Calendar spread with different strikes (directional + time decay)
18. **Ratio Spread** - Unbalanced spread (more contracts on one leg)

## Analysis Workflow

### Step 1: Gather Input Data

**Required from User:**
- Ticker symbol
- Strategy type
- Strike prices
- Expiration date(s)
- Position size (number of contracts)

**Optional from User:**
- Implied Volatility (IV) - if not provided, use Historical Volatility (HV)
- Risk-free rate - default to current 3-month T-bill rate (~5.3% as of 2025)

**Fetched from Robinhood MCP (primary, saved to `scripts/sourced_data/<ticker>.json`):**
- Current stock price (via `get_equity_quotes`)
- Option chain & expiration dates (via `get_option_chains`)
- Option contracts & IDs (via `get_option_instruments`)
- Option quotes with bid/ask, IV, Greeks (via `get_option_quotes`)

**Fetched from FMP API (fallback when Robinhood MCP unavailable or for HV):**
- Historical prices (for HV calculation)
- Dividend yield
- Upcoming earnings date (for earnings strategies)

**Example User Input:**
```
Ticker: AAPL
Strategy: Bull Call Spread
Long Strike: $180
Short Strike: $185
Expiration: 30 days
Contracts: 10
IV: 25% (or use HV if not provided)
```

**Multi-Expiration Analysis:**
- For term structure comparison, fetch data for three expirations: ~0 DTE (nearest weekly), ~30 DTE (nearest monthly), and ~60 DTE (next monthly)
- For each expiration, fetch option instruments for **±5 strikes around ATM** (e.g., if ATM=$180, fetch strikes $150 to $210 in $5 increments)
- Create separate JSON files: `<ticker>_0d.json`, `<ticker>_30d.json`, and `<ticker>_60d.json`
- Each JSON should include a `dte` key (days to expiration); `termstructure_stats.py` uses it, or you can pass `--dte <n>`
- Run `black_scholes.py` separately for each, then `termstructure_stats.py`, then compile a combined report

**Historical Data for Realized Volatility:**
- After fetching stock quote and before writing JSONs, fetch 90 days of daily OHLCV:
  - `get_equity_historicals(symbols=["TICKER"], interval="day", start_time="YYYY-MM-DDT00:00:00Z", end_time="YYYY-MM-DDT00:00:00Z")`
- Extract chronological close prices into a `historical_closes` array in both JSONs
- This enables `--realized-vol` to compute RV-10/20/30/60

### Step 2: Calculate Historical Volatility (if IV not provided)

**Objective:** Estimate volatility from historical price movements.

**Method:**
```python
# Fetch 90 days of price data
prices = get_historical_prices("AAPL", days=90)

# Calculate daily returns
returns = np.log(prices / prices.shift(1))

# Annualized volatility
HV = returns.std() * np.sqrt(252)  # 252 trading days
```

**Output:**
- Historical Volatility (annualized percentage)
- Note to user: "HV = 24.5%, consider using current market IV for more accuracy"

**User Can Override:**
- Provide IV from broker platform (ThinkorSwim, TastyTrade, etc.)
- Script accepts `--iv 28.0` parameter

### Step 3: Price Options Using Black-Scholes

**Black-Scholes Model:**

For European-style options:
```
Call Price = S * N(d1) - K * e^(-r*T) * N(d2)
Put Price = K * e^(-r*T) * N(-d2) - S * N(-d1)

Where:
d1 = [ln(S/K) + (r + σ²/2) * T] / (σ * √T)
d2 = d1 - σ * √T

S = Current stock price
K = Strike price
r = Risk-free rate
T = Time to expiration (years)
σ = Volatility (IV or HV)
N() = Cumulative standard normal distribution
```

**Adjustments:**
- Subtract present value of dividends from S for calls
- American options: Use approximation or note "European pricing, may undervalue American options"

**Python Implementation:**
```python
from scipy.stats import norm
import numpy as np

def black_scholes_call(S, K, T, r, sigma, q=0):
    """
    S: Stock price
    K: Strike price
    T: Time to expiration (years)
    r: Risk-free rate
    sigma: Volatility
    q: Dividend yield
    """
    d1 = (np.log(S/K) + (r - q + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
    d2 = d1 - sigma*np.sqrt(T)

    call_price = S*np.exp(-q*T)*norm.cdf(d1) - K*np.exp(-r*T)*norm.cdf(d2)
    return call_price

def black_scholes_put(S, K, T, r, sigma, q=0):
    d1 = (np.log(S/K) + (r - q + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
    d2 = d1 - sigma*np.sqrt(T)

    put_price = K*np.exp(-r*T)*norm.cdf(-d2) - S*np.exp(-q*T)*norm.cdf(-d1)
    return put_price
```

**Output for Each Option Leg:**
- Theoretical price
- Note: "Market price may differ due to bid-ask spread and American vs European pricing"

### Step 4: Calculate Greeks

**The Greeks** measure option price sensitivity to various factors:

**Delta (Δ):** Change in option price per $1 change in stock price
```python
def delta_call(S, K, T, r, sigma, q=0):
    d1 = (np.log(S/K) + (r - q + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
    return np.exp(-q*T) * norm.cdf(d1)

def delta_put(S, K, T, r, sigma, q=0):
    d1 = (np.log(S/K) + (r - q + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
    return np.exp(-q*T) * (norm.cdf(d1) - 1)
```

**Gamma (Γ):** Change in delta per $1 change in stock price
```python
def gamma(S, K, T, r, sigma, q=0):
    d1 = (np.log(S/K) + (r - q + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
    return np.exp(-q*T) * norm.pdf(d1) / (S * sigma * np.sqrt(T))
```

**Theta (Θ):** Change in option price per day (time decay)
```python
def theta_call(S, K, T, r, sigma, q=0):
    d1 = (np.log(S/K) + (r - q + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
    d2 = d1 - sigma*np.sqrt(T)

    theta = (-S*norm.pdf(d1)*sigma*np.exp(-q*T)/(2*np.sqrt(T))
             - r*K*np.exp(-r*T)*norm.cdf(d2)
             + q*S*norm.cdf(d1)*np.exp(-q*T))

    return theta / 365  # Per day
```

**Vega (ν):** Change in option price per 1% change in volatility
```python
def vega(S, K, T, r, sigma, q=0):
    d1 = (np.log(S/K) + (r - q + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
    return S * np.exp(-q*T) * norm.pdf(d1) * np.sqrt(T) / 100  # Per 1%
```

**Rho (ρ):** Change in option price per 1% change in interest rate
```python
def rho_call(S, K, T, r, sigma, q=0):
    d2 = (np.log(S/K) + (r - q + 0.5*sigma**2)*T) / (sigma*np.sqrt(T)) - sigma*np.sqrt(T)
    return K * T * np.exp(-r*T) * norm.cdf(d2) / 100  # Per 1%
```

**Position Greeks:**

For a strategy with multiple legs, sum Greeks across all legs:
```python
# Example: Bull Call Spread
# Long 1x $180 call
# Short 1x $185 call

delta_position = (1 * delta_long) + (-1 * delta_short)
gamma_position = (1 * gamma_long) + (-1 * gamma_short)
theta_position = (1 * theta_long) + (-1 * theta_short)
vega_position = (1 * vega_long) + (-1 * vega_short)
```

**Greeks Interpretation:**

| Greek | Meaning | Example |
|-------|---------|---------|
| **Delta** | Directional exposure | Δ = 0.50 → $50 profit if stock +$1 |
| **Gamma** | Delta acceleration | Γ = 0.05 → Delta increases by 0.05 if stock +$1 |
| **Theta** | Daily time decay | Θ = -$5 → Lose $5/day from time passing |
| **Vega** | Volatility sensitivity | ν = $10 → Gain $10 if IV increases 1% |
| **Rho** | Interest rate sensitivity | ρ = $2 → Gain $2 if rates increase 1% |

### Step 5: Simulate Strategy P/L

**Objective:** Calculate profit/loss at various stock prices at expiration.

**Method:**

Generate stock price range (e.g., ±30% from current price):
```python
current_price = 180
price_range = np.linspace(current_price * 0.7, current_price * 1.3, 100)
```

For each price point, calculate P/L:
```python
def calculate_pnl(strategy, stock_price_at_expiration):
    pnl = 0

    for leg in strategy.legs:
        if leg.type == 'call':
            intrinsic_value = max(0, stock_price_at_expiration - leg.strike)
        else:  # put
            intrinsic_value = max(0, leg.strike - stock_price_at_expiration)

        if leg.position == 'long':
            pnl += (intrinsic_value - leg.premium_paid) * 100  # Per contract
        else:  # short
            pnl += (leg.premium_received - intrinsic_value) * 100

    return pnl * num_contracts
```

**Key Metrics:**
- **Max Profit**: Highest possible P/L
- **Max Loss**: Worst possible P/L
- **Breakeven Point(s)**: Stock price(s) where P/L = 0
- **Profit Probability**: Percentage of price range that's profitable (simplified)

**Example Output:**
```
Bull Call Spread: $180/$185 on AAPL (30 DTE, 10 contracts)

Current Price: $180.00
Net Debit: $2.50 per spread ($2,500 total)

Max Profit: $2,500 (at $185+)
Max Loss: -$2,500 (at $180-)
Breakeven: $182.50
Risk/Reward: 1:1

Probability Profit: ~55% (if stock stays above $182.50)
```

### Step 6: Generate P/L Diagram (ASCII Art)

**Visual representation of P/L across stock prices:**

```python
def generate_pnl_diagram(price_range, pnl_values, current_price, width=60, height=15):
    """Generate ASCII P/L diagram"""

    # Normalize to chart dimensions
    max_pnl = max(pnl_values)
    min_pnl = min(pnl_values)

    lines = []
    lines.append(f"\nP/L Diagram: {strategy_name}")
    lines.append("-" * width)

    # Y-axis levels
    levels = np.linspace(max_pnl, min_pnl, height)

    for level in levels:
        if abs(level) < (max_pnl - min_pnl) * 0.05:
            label = f"    0 |"  # Zero line
        else:
            label = f"{level:6.0f} |"

        row = label
        for i in range(width - len(label)):
            idx = int(i / (width - len(label)) * len(price_range))
            pnl = pnl_values[idx]
            price = price_range[idx]

            # Determine character
            if abs(pnl - level) < (max_pnl - min_pnl) / height:
                if pnl > 0:
                    char = '█'  # Profit
                elif pnl < 0:
                    char = '░'  # Loss
                else:
                    char = '─'  # Breakeven
            elif abs(level) < (max_pnl - min_pnl) * 0.05:
                char = '─'  # Zero line
            elif abs(price - current_price) < (price_range[-1] - price_range[0]) * 0.02:
                char = '│'  # Current price line
            else:
                char = ' '

            row += char

        lines.append(row)

    lines.append(" " * 6 + "|" + "-" * (width - 6))
    lines.append(" " * 6 + f"${price_range[0]:.0f}" + " " * (width - 20) + f"${price_range[-1]:.0f}")
    lines.append(" " * (width // 2 - 5) + "Stock Price")

    return "\n".join(lines)
```

**Example Output:**
```
P/L Diagram: Bull Call Spread $180/$185
------------------------------------------------------------
 +2500 |                               ████████████████████
       |                         ██████
       |                   ██████
       |             ██████
     0 |       ──────
       | ░░░░░░
       |░░░░░░
 -2500 |░░░░░
      |____________________________________________________________
       $126                  $180                   $234
                          Stock Price

Legend: █ Profit  ░ Loss  ── Breakeven  │ Current Price
```

### Step 7: Strategy-Specific Analysis

Provide tailored guidance based on strategy type:

**Covered Call:**
```
Income Strategy: Generate premium while capping upside

Setup:
- Own 100 shares of AAPL @ $180
- Sell 1x $185 call (30 DTE) for $3.50

Max Profit: $850 (Stock at $185+ = $5 stock gain + $3.50 premium)
Max Loss: Unlimited downside (stock ownership)
Breakeven: $176.50 (Cost basis - premium received)

Greeks:
- Delta: -0.30 (reduces stock delta from 1.00 to 0.70)
- Theta: +$8/day (time decay benefit)

Assignment Risk: If AAPL > $185 at expiration, shares called away

When to Use:
- Neutral to slightly bullish
- Want income in sideways market
- Willing to sell stock at $185

Exit Plan:
- Buy back call if stock rallies strongly (preserve upside)
- Let expire if stock stays below $185
- Roll to next month if want to keep shares
```

**Protective Put:**
```
Insurance Strategy: Limit downside while keeping upside

Setup:
- Own 100 shares of AAPL @ $180
- Buy 1x $175 put (30 DTE) for $2.00

Max Profit: Unlimited (stock can rise infinitely)
Max Loss: -$7 per share = ($5 stock loss + $2 premium)
Breakeven: $182 (Cost basis + premium paid)

Greeks:
- Delta: +0.80 (stock delta 1.00 - put delta 0.20)
- Theta: -$6/day (time decay cost)

Protection: Guaranteed to sell at $175, no matter how far stock falls

When to Use:
- Own stock, worried about short-term drop
- Earnings coming up, want protection
- Alternative to stop-loss (can't be stopped out)

Cost: "Insurance premium" - typically 1-3% of stock value

Exit Plan:
- Let expire worthless if stock rises (cost of insurance)
- Exercise put if stock falls below $175
- Sell put if stock drops but want to keep shares
```

**Iron Condor:**
```
Range-Bound Strategy: Profit from low volatility

Setup (example on AAPL @ $180):
- Sell $175 put for $1.50
- Buy $170 put for $0.50
- Sell $185 call for $1.50
- Buy $190 call for $0.50

Net Credit: $2.00 ($200 per iron condor)

Max Profit: $200 (if stock stays between $175-$185)
Max Loss: $300 (if stock moves outside $170-$190)
Breakevens: $173 and $187
Profit Range: $175 to $185 (58% probability)

Greeks:
- Delta: ~0 (market neutral)
- Theta: +$15/day (time decay benefit)
- Vega: -$25 (short volatility)

When to Use:
- Expect low volatility, range-bound movement
- After big move, think consolidation
- High IV environment (sell expensive options)

Risk: Unlimited if one side tested
- Use stop loss at 2x credit received (exit at -$400)

Adjustments:
- If tested on one side, roll that side out in time
- Close early at 50% max profit to reduce tail risk
```

### Step 8: Earnings Strategy Analysis

**Integration with Earnings Calendar:**

When user asks about earnings strategies, fetch earnings date:
```python
from earnings_calendar import get_next_earnings_date

earnings_date = get_next_earnings_date("AAPL")
days_to_earnings = (earnings_date - today).days
```

**Pre-Earnings Strategies:**

**Long Straddle/Strangle:**
```
Setup (AAPL @ $180, earnings in 7 days):
- Buy $180 call for $5.00
- Buy $180 put for $4.50
- Total Cost: $9.50

Thesis: Expect big move (>5%) but unsure of direction

Breakevens: $170.50 and $189.50
Profit if: Stock moves >$9.50 in either direction

Greeks:
- Delta: ~0 (neutral)
- Vega: +$50 (long volatility)
- Theta: -$25/day (time decay hurts)

IV Crush Risk: ⚠️ CRITICAL
- Pre-earnings IV: 40% (elevated)
- Post-earnings IV: 25% (typical)
- IV drop: -15 points = -$750 loss even if stock doesn't move!

Analysis:
- Implied Move: √(DTE/365) × IV × Stock Price
  = √(7/365) × 0.40 × 180 = ±$10.50
- Breakeven Move Needed: ±$9.50
- Probability Profit: ~30-40% (implied move > breakeven move)

Recommendation:
✅ Consider if you expect >10% move (larger than implied)
❌ Avoid if expect normal ~5% earnings move (IV crush will hurt)

Alternative: Buy further OTM strikes to reduce cost
- $175/$185 strangle cost $4.00 (need >$8 move, but cheaper)
```

**Short Iron Condor:**
```
Setup (AAPL @ $180, earnings in 7 days):
- Sell $170/$175 put spread for $2.00
- Sell $185/$190 call spread for $2.00
- Net Credit: $4.00

Thesis: Expect stock to stay range-bound ($175-$185)

Profit Zone: $175 to $185
Max Profit: $400
Max Loss: $100

IV Crush Benefit: ✅
- Short high IV before earnings
- IV drops after earnings → profit on vega
- Even if stock moves slightly, IV drop helps

Greeks:
- Delta: ~0 (market neutral)
- Vega: -$40 (short volatility - good here!)
- Theta: +$20/day

Recommendation:
✅ Good if expect normal earnings reaction (<8% move)
✅ Benefit from IV crush regardless of direction
⚠️ Risk if stock gaps outside range (>10% move)

Exit Plan:
- Close next day if IV crushed (capture profit early)
- Use stop loss if one side tested (-2x credit)
```

### Step 9: Risk Management Guidance

**Position Sizing:**

```
Account Size: $50,000
Risk Tolerance: 2% per trade = $1,000 max risk

Iron Condor Example:
- Max loss per spread: $300
- Max contracts: $1,000 / $300 = 3 contracts
- Actual position: 3 iron condors

Bull Call Spread Example:
- Debit paid: $2.50 per spread
- Max contracts: $1,000 / $250 = 4 contracts
- Actual position: 4 spreads
```

**Portfolio Greeks Management:**

```
Portfolio Guidelines:
- Delta: -10 to +10 (mostly neutral)
- Theta: Positive preferred (seller advantage)
- Vega: Monitor if >$500 (IV risk)

Current Portfolio:
- Delta: +5 (slightly bullish)
- Theta: +$150/day (collecting $150 daily)
- Vega: -$300 (short volatility)

Interpretation:
✅ Neutral delta (safe)
✅ Positive theta (time working for you)
⚠️ Short vega: If IV spikes, lose $300 per 1% IV increase
→ Reduce short premium positions if VIX rising
```

**Adjustments and Exits:**

```
Exit Rules by Strategy:

Covered Call:
- Profit: 50-75% of max profit
- Loss: Stock drops >5%, buy back call to preserve upside
- Time: 7-10 DTE, roll to avoid assignment

Spreads:
- Profit: 50% of max profit (close early, reduce tail risk)
- Loss: 2x debit paid (cut losses early)
- Time: 21 DTE, close or roll (avoid gamma risk)

Iron Condor:
- Profit: 50% of credit (close early common)
- Loss: One side tested, 2x credit lost
- Adjustment: Roll tested side out in time

Straddle/Strangle:
- Profit: Stock moved >breakeven, close immediately
- Loss: Theta eating position, stock not moving
- Time: Day after earnings (if earnings play)
```

### Step 10: Analyze Across Multiple Expirations (Term Structure)

**Objective:** Compare Black-Scholes pricing accuracy and option characteristics across short-term (~30 DTE) and medium-term (~60 DTE) expirations.

**Workflow:**

1. **Identify expirations:**
   - Nearest monthly expiry closest to 30 DTE
   - Next monthly expiry closest to 60 DTE

2. **Fetch data for each expiration:**
   - `get_option_instruments(chain_id=..., expiration_dates="YYYY-MM-DD", ...)`
   - Include strikes from ATM-5 to ATM+5 (11 strikes minimum)
   - `get_option_quotes(instrument_ids=[...])` for each set

3. **Write JSON files:**
   - `scripts/sourced_data/<ticker>_30d.json` — must include `"ticker"`, `"expiration"`, `"dte"`, `"stock_price"`, `"historical_closes"`, and `"options"` array (strike, type, bid, ask, iv, delta, gamma, theta, vega)
   - `scripts/sourced_data/<ticker>_0d.json` and `<ticker>_60d.json` — same structure
   - The `ticker` and `expiration` fields are required by `fetch_oi_volume.py` to auto-discover and process files; `dte` is used by `termstructure_stats.py` (or pass `--dte <n>`)
   - **Never estimate data** — every number in the report must come from a fetched source, a computed derivation (BS model, RV, IV stats), or a BS model run. If a strike lacks a market quote, either fetch it or note it as unavailable. Do not fill gaps with guesses.

4. **Run yfinance fallback** (OI/Volume + IV Profile):
   ```bash
   C:\Python314\python.exe scripts\fetch_oi_volume.py
   ```
   This patches `volume`/`open_interest` on every JSON in `scripts/sourced_data/` and prints IV Rank, IV Percentile, and 52-week HV range for each ticker.

5. **Run Black-Scholes for each with `--realized-vol`:**
   ```bash
   C:\Python314\python.exe scripts\black_scholes.py --market-data scripts/sourced_data/<ticker>_30d.json --strike <ATM> --days 30 --realized-vol
   C:\Python314\python.exe scripts\black_scholes.py --market-data scripts/sourced_data/<ticker>_60d.json --strike <ATM> --days 66 --realized-vol
   ```

6. **Run term-structure stats for all three expirations** (expected move, lognormal probabilities, PC ratios, per-strike OI/volume, put−call IV skew):
   ```bash
   C:\Python314\python.exe scripts\termstructure_stats.py --market-data scripts/sourced_data/<ticker>_0d.json scripts/sourced_data/<ticker>_30d.json scripts/sourced_data/<ticker>_60d.json
   ```
   Optionally `--levels 120 130 140 150` to pin probability levels, or `--format markdown` for report-ready tables. Uses the `dte` key in the JSON; for JSONs lacking it, pass `--dte <n>`.

7. **Build At-Expiry payoff matrices for the report's trade ideas** (straddle/bull_call/bear_put/short_put, supplied via a strategies JSON; `--probability` adds a prob-of-profit row computed from the JSON's IV/DTE):
   ```bash
   C:\Python314\python.exe scripts\payoff_matrix.py --market-data scripts/sourced_data/<ticker>_30d.json --strategies scripts/examples/strategies_30d.json --levels 110 125 135 160 --probability
   ```
   See `scripts/examples/strategies_30d.json` for the strategies schema.

8. **Compile 13-section combined report** (see template below):

   | # | Section | Content |
   |---|---------|---------|
   | 1 | Summary | Key metrics table with Expected Move row |
    | 2 | Volatility Context | IV vs RV table, RV Regime (10/20/30/60d), IV Profile (Rank/Percentile from yfinance) |
   | 3 | Expected Move | 1SD range, Probability Estimates (lognormal z-scores) |
   | 4 | IV Skew (32 DTE) | Strike IV table with caveats |
   | 5 | IV Skew (60 DTE) | Strike IV table with caveats |
   | 6 | Open Interest & Volume | Per-strike OI, volume, PC Vol Ratio, PC OI Ratio (source: yfinance) |
   | 7 | Greeks Comparison | ATM Greeks side-by-side |
   | 8 | BS Validation | Theoretical vs market prices |
   | 9 | Vol Term Structure | IV across expirations |
   | 10 | Time Decay Comparison | Theta as % of premium |
    | 11 | Trade Ideas | Defined-risk strategies first; Vol Thesis Assessment callout |
   | 12 | Risk Metrics | IV level, vol thesis, expected move, skew, etc. |
   | 13 | Day-over-Day Context | Price change context |

---

## Output Format

```markdown
# Options Strategy Analysis: [Strategy Name]

**Symbol:** [TICKER]
**Strategy:** [Strategy Type]
**Expiration:** [Date] ([DTE] days)
**Contracts:** [Number]

---

## Strategy Setup

### Leg Details
| Leg | Type | Strike | Price | Position | Quantity |
|-----|------|--------|-------|----------|----------|
| 1 | Call | $180 | $5.00 | Long | 1 |
| 2 | Call | $185 | $2.50 | Short | 1 |

**Net Debit/Credit:** $2.50 debit ($250 total for 1 spread)

---

## Profit/Loss Analysis

**Max Profit:** $250 (at $185+)
**Max Loss:** -$250 (at $180-)
**Breakeven:** $182.50
**Risk/Reward Ratio:** 1:1

**Probability Analysis:**
- Probability of Profit: ~55% (stock above $182.50)
- Expected Value: $25 (simplified)

---

## P/L Diagram

[ASCII art diagram here]

---

## Greeks Analysis

### Position Greeks (1 spread)
- **Delta:** +0.20 (gains $20 if stock +$1)
- **Gamma:** +0.03 (delta increases by 0.03 if stock +$1)
- **Theta:** -$5/day (loses $5 per day from time decay)
- **Vega:** +$8 (gains $8 if IV increases 1%)

### Interpretation
- **Directional Bias:** Slightly bullish (positive delta)
- **Time Decay:** Working against you (negative theta)
- **Volatility:** Benefits from IV increase (positive vega)

---

## Risk Assessment

### Maximum Risk
**Scenario:** Stock falls below $180
**Max Loss:** -$250 (100% of premium paid)
**% of Account:** 0.5% (if $50k account)

### Assignment Risk
**Early Assignment:** Low (calls have time value)
**At Expiration:** Manage positions if in-the-money

---

## Trade Management

### Entry
✅ Enter if: [Conditions]
- Stock price $178-$182
- IV below 30%
- >21 DTE

### Profit Taking
- **Target 1:** 50% profit ($125) - Close half
- **Target 2:** 75% profit ($187.50) - Close all

### Stop Loss
- **Trigger:** Stock falls below $177 (-$150 loss)
- **Action:** Close position immediately

### Adjustments
- If stock rallies to $184, consider rolling short call higher
- If stock drops to $179, add second spread at $175/$180

---

## Suitability

### When to Use This Strategy
✅ Moderately bullish on AAPL
✅ Expect upside to $185-$190
✅ Want defined risk
✅ 21-45 DTE timeframe

### When to Avoid
❌ Very bullish (buy stock or long call instead)
❌ High IV environment (wait for IV to drop)
❌ Earnings in <7 days (IV crush risk)

---

## Alternatives Comparison

| Strategy | Max Profit | Max Loss | Complexity | When Better |
|----------|-----------|----------|------------|-------------|
| Bull Call Spread | $250 | -$250 | Medium | Moderately bullish |
| Long Call | Unlimited | -$500 | Low | Very bullish |
| Covered Call | $850 | Unlimited | Medium | Own stock already |
| Bull Put Spread | $300 | -$200 | Medium | Want credit spread |

**Recommendation:** Bull call spread is good balance of risk/reward for moderate bullish thesis.

---

*Disclaimer: This is theoretical analysis using Black-Scholes pricing. Actual market prices may differ. Trade at your own risk. Options are complex instruments with significant loss potential.*
```

**Multi-Expiration Term Structure Report Template:**

Every report must include ALL of the following sections in this exact order:

```markdown
# [TICKER] Options Term Structure Analysis

**Date:** YYYY-MM-DD | **Price:** $XX.XX | **Prev Close:** $XX.XX (change%) | **Source:** Robinhood MCP

---

## 1. Summary

| Metric | [N] DTE ([Expiry]) | [N] DTE ([Expiry]) | Change |
|--------|:-:|:-:|:-:|
| Stock Price | $XX.XX | $XX.XX | — |
| ATM Call IV | XX% (@ $X) | XX% (@ $X) | ±Xpp |
| ATM Put IV | XX% (@ $X) | XX% (@ $X) | ±Xpp |
| ATM Call Mid | $X.XX | $X.XX | ±X% |
| ATM Put Mid | $X.XX | $X.XX | ±X% |
| Put Skew | ~Xpp | ~Xpp | — |
| Strike Count | X ($X-$X) | X ($X-$X) | — |
| **IV Term Structure** | **~X%** | **~X%** | **Shape** |
| **Expected Move (1SD)** | **~$X** | **~$X** | — |

**Takeaway:** [1-2 sentence summary of key findings]

---

## 2. Volatility Context

### Implied Volatility vs Realized Volatility

| Metric | Value | Source |
|--------|:-----:|--------|
| Current ATM IV | ~X% | Robinhood MCP |
| IV Rank | X% | yfinance (compute_iv_stats) |
| IV Percentile | X% | yfinance (compute_iv_stats) |
| 52-Week HV Range | X% – X% | yfinance (compute_iv_stats) |

### Realized Volatility Regime

| Period | RV | IV/RV | Direction |
|--------|:--:|:-----:|:----------|
| 10-day | **X%** | X.XXx | RV > IV |
| 20-day | **X%** | X.XXx | RV > IV |
| 30-day | **X%** | X.XXx | RV > IV |
| 60-day | **X%** | X.XXx | RV > IV |

**Trend:** [Accelerating/Decelerating/Plateauing — describe RV direction]

### IV / RV Ratios

| Ratio | Value | Interpretation |
|-------|:-----:|:--------|
| IV / RV-10 | X.XXx | Market pricing X% [above/below] 10-day vol |
| IV / RV-20 | X.XXx | ... |
| IV / RV-30 | X.XXx | ... |
| IV / RV-60 | X.XXx | ... |

**Key insight:** IV is pricing [X% below/above] recent realized vol. This does not mean options are "cheap" — it means the market [expects mean reversion / expects sustained vol]. If you agree with [direction], [recommendation].

### IV Profile

| Metric | Value | Meaning |
|--------|:-----:|---------|
| IV Rank | X% | Position within 52-week HV range |
| IV Percentile | X% | % of days with lower rolling 30d HV |
| 52-Week HV Range | X% – X% | Min/max rolling 30d HV over past year |

**Caveats:**
- IV Rank is **historical** — it compares current IV to past realized vol. A high rank does not mean IV is overpriced; it may be justified by recent RV.
- During regime shifts (structural repricing, sector crises), IV can stay elevated or expand further — examples: March 2020, Oct 2022, Apr 2025.
- The key question: is this a **temporary vol spike** or a **structural regime change**? Compare IV to RV-10/RV-20. IV ≈ RV-10 suggests efficient pricing.
- IV Rank alone is not a short-vol signal. Short premium strategies during high IV carry tail risk — the market is pricing that risk for a reason.

**Verdict:** IV (X%) sits [above/below] RV-30 (X%). [Describe whether recent RV justifies current IV level.]

---

## 3. Expected Move (1 Standard Deviation)

```
Expected Move = Stock Price × IV × √(DTE / 365)
```

| Expiry | DTE | Avg IV | 1SD Move | Lower Bound | Upper Bound |
|--------|:---:|:------:|:--------:|:-----------:|:-----------:|
| [Name] | N | X% | **~$X** | **$X** | **$X** |

**Interpretation:** The market prices a 68% probability that the stock stays within these bounds.

### Probability Estimates (Lognormal Model)

Produced by `scripts/termstructure_stats.py` (lognormal via `z = ln(K / S) / (σ√T)`):

| Level | Approx Probability |
|-------|:-----------------:|
| Above $X | ~X% |
| Below $X | ~X% |

`z = ln(K / S) / (σ√T)`, then standard normal CDF.

**Fat-Tail Warning After Large Moves:**
- The lognormal model assumes returns are normally distributed. Empirical returns have **fatter tails** — extreme moves occur more often than the model predicts.
- This is especially true **after a large single-day move** (e.g., a 7% sell-off). The conditional distribution is not lognormal — volatility clustering means another large move in either direction is more likely than the model implies.
- **Practical implication:** A short put showing "82% probability of profit" under Black-Scholes may have significantly lower odds in reality. The probability numbers should be treated as relative rankings between strikes, not absolute forecasts.
- **Best practice:** Use lognormal probabilities for comparing relative likelihood of different strikes, but always note the fat-tail caveat when presenting absolute probabilities — especially after large price moves.

**Trade context:**
- **Long Straddle**: ~X% total probability of profit
- **Bull Call Spread**: ~X% probability of profit
- **Short Put**: ~X% probability of assignment

---

## 4. IV Skew — [N] DTE ([Expiry])

[Strike-by-strike IV table for 32 DTE]

**Skew shape:** [Describe pattern — e.g., flat, inverted, steep]. 

**Caveats on Skew Interpretation:**
- For **ETFs and index-like products** (e.g., SMH, SPY, QQQ), flat skew is common and expected — these are not single stocks and may not exhibit the typical equity skew premium for downside protection.
- A flat skew does not necessarily mean the market sees low downside risk. It may reflect: elevated call demand from sector optimism, dealer positioning that suppresses put skew, or the structural characteristics of an ETF basket.
- For single stocks, skew inversion may reflect call demand, reduced put demand, dealer positioning, or data artifacts.
- Without OI and trade direction data, the root cause of skew shape cannot be determined from IV alone.

---

## 5. IV Skew — [N] DTE ([Expiry])

[Strike-by-strike IV table for 60 DTE]

**Skew shape:** [Same caveats as above — especially note if the underlying is an ETF or index]

---

## 6. Open Interest & Volume Analysis

### ~[N] DTE ([Expiry])

| Strike | Type | OI | Volume | PC Vol Ratio | PC OI Ratio |
|--------|:---:|:--:|:------:|:-----------:|:-----------:|
| $X | Call | X | X | — | — |
| $X | Put | X | X | X.XXx | X.XXx |

### ~[N] DTE ([Expiry])

| Strike | Type | OI | Volume | PC Vol Ratio | PC OI Ratio |
|--------|:---:|:--:|:------:|:-----------:|:-----------:|
| $X | Call | X | X | — | — |
| $X | Put | X | X | X.XXx | X.XXx |

**Data source:** `scripts/termstructure_stats.py` (Robinhood quotes, or yfinance fallback via `fetch_oi_volume.py`).

**Interpretation:** [Describe notable OI concentration, volume spikes, or put/call imbalance.]

**Caveats on Volume Interpretation:**
- **Volume alone cannot determine direction.** A 4,000-lot put trade could be: opening long puts, closing short puts, opening short puts, closing long puts, part of a multi-leg spread, or dealer hedging. The same raw volume number can mean opposite things.
- **OI change is required to infer sentiment.** Rising OI + rising volume → new positions being established. Rising volume + flat/falling OI → day trading or closing activity (same-day opening and closing). Without OI delta from consecutive quotes, volume is ambiguous.
- **Spreads and hedges confound interpretation.** A put vertical spread involves buying and selling different puts — the volume appears bullish and bearish simultaneously. Dealers hedge directional flow, creating volume that does not reflect end-investor sentiment.
- **Best practice:** Report raw numbers (PC Vol Ratio, PC OI Ratio, OI concentration) neutrally. Note what is knowable (which strikes have activity) and what is not (direction, intent, spread context). Avoid labeling volume as "bearish" or "bullish."

---

## 7. Greeks Comparison (ATM Strikes)

[Greek tables for each expiration]

---

## 8. Black-Scholes Validation

| Contract | BS Price | Market Mid | Diff | Within Spread? |
|----------|:--------:|:----------:|:----:|:-------------:|

**Notable:** For large discrepancies, say: "unresolved pricing discrepancy requiring further validation" — NOT "put-call parity breakdown".

---

## 9. Volatility Term Structure

| Expiry | DTE | ATM Call IV | ATM Put IV | Avg IV | 1SD Expected Move |
|--------|:---:|:----------:|:----------:|:------:|:-----------------:|

---

## 10. Time Decay Comparison (ATM)

| DTE | Call Theta | Put Theta | Decay as % of Premium (Call) |

---

## 11. Trade Ideas

> ⚠ **Vol Thesis Assessment:** The IV/RV analysis shows IV [above/below/broadly inline with] recent realized vol. [Describe which strategies align with current conditions. In high-IV regimes, vertical spreads and defined-risk structures are generally preferred over naked premium or long premium.]

**Trade Selection Guidance:**

| Regime | Favor | Avoid |
|--------|-------|-------|
| IV ≈ RV (efficient pricing) | Any strategy; directional bias is the deciding factor | — |
| IV above recent RV (IV rich) | Credit spreads, defined-risk short premium | Naked short puts/calls (tail risk), naked long premium (paying elevated IV without edge) |
| IV below recent RV (IV cheap) | Debit spreads, long premium strategies | Short premium strategies (under-compensated for realized risk) |
| Post-large-move (7%+ single day) | Defined-risk verticals (bear call spreads, put debit spreads, iron condors) | Naked short puts (fat-tail risk), naked long premium (buying at vol peak), long straddles (too expensive, low historical win rate after vol expansion) |

**General Guidance:**
- **Avoid buying naked premium after a volatility spike.** Historical expectancy of long premium is poor when IV Rank > 75 — you are paying elevated IV, elevated gamma, and elevated fear premium. You need both continued direction and sustained IV to win.
- **Defined-risk verticals** (bear call spreads, bull put spreads, put debit spreads, call debit spreads) let you express a directional view without paying for all of the elevated volatility. They benefit from defined max loss and lower capital at risk.
- **Iron condors and short strangles** (tightly managed) are appropriate when IV > RV-30/RV-60 and the term structure is descending, as they benefit from IV contraction and time decay. Keep wings wide enough to avoid pin risk.
- If you lack directional conviction, consider waiting. Elevated IV after a large move is not an obligation to trade.

> ⚠ **Probability caution:** All lognormal-derived probabilities assume normally distributed returns. After a large move, empirical tails are fatter than Black-Scholes assumes. Actual probability of extreme moves is higher than model estimates.

### 1. [Trade Name] — [Aligned/Contrarian to Vol Thesis]
- Setup details
- Breakeven(s)
- **Probability:** ~X% [profit/assignment]
- **Expected move context:** How trade relates to 1SD range

[Repeat for each trade idea — order defined-risk strategies first, then others]

### At-Expiry Payoff

Produced by `scripts/payoff_matrix.py` from an analyst-supplied strategies JSON (`type` ∈ straddle/bull_call/bear_put/short_put with strikes + cost/credit). Run once per expiration; `--probability` appends a prob-of-profit row computed from the JSON's IV/DTE.

#### ~[N] DTE

| Price Level | [Straddle] | [Bull Call] | [Bear Put] | [Short Put] |
|-------------|:----------:|:-----------:|:----------:|:-----------:|
| $XXX (deep down) | Gain | Lose | Max Gain | Assigned |
| $XXX (near down) | Lose | Lose | Partial Gain | Keep Premium |
| $XXX (near up) | Lose | Partial Gain | Lose | Keep Premium |
| $XXX (deep up) | Gain | Max Gain | Lose | Keep Premium |

#### ~[N] DTE

| Price Level | [Straddle] | [Bull Call] | [Bear Put] | [Short Put] |
|-------------|:----------:|:-----------:|:----------:|:-----------:|
| $XXX (deep down) | Gain | Lose | Max Gain | Assigned |
| $XXX (near down) | Lose | Lose | Partial Gain | Keep Premium |
| $XXX (near up) | Lose | Partial Gain | Lose | Keep Premium |
| $XXX (deep up) | Gain | Max Gain | Lose | Keep Premium |

**Payoff labels:**
- **Gain** — any profit
- **Max Gain** — strategy at maximum profit
- **Lose** — any loss
- **Max Loss** — strategy at maximum loss
- **Partial Gain** — some profit, not max
- **Assigned** — short put assigned (obligation to buy shares)
- **Keep Premium** — short put expired worthless

### Strategy Matrix

| Strategy | Direction | Vol Thesis Fit | Prob of Profit | Risk |

---

## 12. Risk Metrics

| Risk Factor | Assessment |
|-------------|:-----------|
| IV Level | |
| IV/RV Disconnect | |
| Vol Thesis Conflict | |
| Expected Move | |
| Term Structure | |
| Put/Call Skew | |
| Liquidity | |
| BS Fit | |
| Day Change | |
| Call-Put Parity (32d) | Unresolved pricing discrepancy requiring further validation |

---

## 13. Day-over-Day Context

| Metric | Value | Note |

---

*Generated: YYYY-MM-DD HH:MM UTC*
*Model: Black-Scholes (European options pricing)*
*Data: Robinhood MCP (primary), yfinance (OI/volume + IV stats fallback)*
```

**File Naming Convention:**
```
output/<stock>_options_<strategy>_<datetimestamp>.md
```
- Stored under the `output/` folder
- Datetime format: `YYYYMMDD_HHmmss` (24-hour)

Examples:
- Single strategy: `output/AAPL_options_bullcall_20260616_143000.md`
- Multi-expiration term structure: `output/AAPL_options_termstructure_20260616_153000.md`
- General analysis: `output/BMNR_options_analysis_20260616_150944.md`

## Key Principles

### Theoretical Pricing Limitations

**What Users Should Know:**
1. **Black-Scholes Assumptions:**
   - European-style options (can't exercise early)
   - Constant volatility (IV changes in reality)
   - No transaction costs
   - Continuous trading

2. **Real vs Theoretical:**
   - Bid-ask spread: Actual cost higher than theoretical
   - American options: Can be exercised early (especially ITM puts)
   - Liquidity: Wide markets on illiquid options
   - Dividends: Ex-dividend dates affect pricing

3. **Best Practices:**
   - Use as educational tool and comparative analysis
   - Get real quotes from broker before trading
   - Understand theoretical price ≈ mid-market price
   - Account for commissions and slippage

### Volatility Guidance

**Historical vs Implied Volatility:**

```
Historical Volatility (HV): What happened
- Calculated from past price movements
- Objective, based on data
- Available for free (FMP API)

Implied Volatility (IV): What market expects
- Derived from option prices
- Subjective, based on supply/demand
- Requires live options data (user provides)

Comparison:
- IV > HV: Options expensive (consider selling)
- IV < HV: Options cheap (consider buying)
- IV = HV: Fairly priced
```

**IV Rank & Percentile (yfinance):**

Computed automatically by `scripts/fetch_oi_volume.py` after the OI/volume patch. Downloads 1 year of daily OHLCV via yfinance, computes rolling 30-day annualized HV, then ranks the current ATM IV against that distribution:

```python
from scripts.fetch_oi_volume import compute_iv_stats

stats = compute_iv_stats("AAPL", current_iv=0.28)
# Returns: {"iv_rank": 42.2, "iv_percentile": 54.0,
#           "hv_high_52w": 35.1, "hv_low_52w": 18.2,
#           "num_readings": 222}
```

| Metric | Meaning |
|--------|---------|
| IV Rank | Position within 52-week HV range (0-100%). <25% = relatively low, >75% = relatively high |
| IV Percentile | % of days HV was lower. <25 = historically cheap, >75 = historically expensive |
| 52-Week HV Range | Min/max rolling 30-day HV over the past year |

**Critical Caveats:**

| Caveat | Explanation |
|--------|-------------|
| **IV Rank is historical, not predictive** | It compares current IV to *past* realized vol. It tells you where vol has been, not where it's going. During a regime shift (sustained high vol), high IV can persist or go higher — March 2020, October 2022, and April 2025 all featured IV that looked "historically expensive" and then expanded further. |
| **IV Percentile does not mean overpriced** | "99.5th percentile expensive" means HV has been lower 99.5% of the time in the past year. But if the market has regime-shifted (e.g., a sector-wide repricing), the new baseline vol may be structurally higher. The metric is descriptive, not prescriptive. |
| **Compare against recent RV** | IV at the 99th percentile may be fully justified if RV-10 is at a similar level. The key question is: is this a temporary vol spike or a structural regime change? IV ≈ RV-10 suggests efficient pricing, not overpricing. |
| **Does not predict direction** | High IV Rank alone is not a short-vol signal. During crises, IV can remain elevated for extended periods. Short premium strategies (naked short puts/calls, short straddles) carry significant tail risk when IV is high — the market is pricing that risk for a reason. |

**Contextual Decision Framework:**

Instead of mechanical thresholds, use this framework:

```
IV Rank < 25 AND RV-10 < IV (IV above recent vol):
  → Options historically cheap AND market overpricing vol
  → Favor long premium strategies if directional conviction exists

IV Rank < 25 AND RV-10 > IV:
  → Options historically cheap BUT market underpricing relative to recent vol
  → Long premium may still work; prefer debit spreads for defined risk

IV Rank > 75 AND RV-10 > IV (IV below recent vol):
  → Options historically expensive BUT justified by recent realized vol
  → Efficient pricing; defined-risk credit spreads superior to naked short

IV Rank > 75 AND RV-10 < IV:
  → Options historically expensive AND IV above recent vol
  → Best case for premium selling; prefer defined-risk (iron condors, credit spreads)
  → Naked short carries tail risk — vol can expand further in crisis
```

## Integration with Other Skills

**Earnings Calendar:**
- Fetch earnings dates automatically
- Suggest earnings-specific strategies
- Calculate days to earnings (DTE critical for IV)
- Warn about IV crush risk

**Technical Analyst:**
- Use support/resistance for strike selection
- Trend analysis for directional strategies
- Breakout potential for straddle/strangle timing

**US Stock Analysis:**
- Fundamental analysis for longer-term strategies (LEAPS)
- Dividend yield for covered call/put analysis
- Earnings quality for earnings plays

**Bubble Detector:**
- High bubble risk → focus on protective puts
- Low risk → bullish strategies
- Critical risk → avoid long premium (theta hurts)

**Portfolio Manager:**
- Track options positions alongside stock positions
- Aggregate Greeks across portfolio
- Options as hedging tool for stock positions

## Important Notes

- **All analysis in English**
- **Educational focus**: Strategies explained clearly
- **Theoretical pricing**: Black-Scholes approximation
- **User IV input**: Optional, defaults to HV
- **Live data via Robinhood MCP**: Stock quotes, option chains, bids/asks, IV, Greeks fetched by agent and saved to `scripts/sourced_data/<ticker>.json`
- **FMP API fallback**: Historical volatility, dividends, earnings dates (requires `FMP_API_KEY` env var)
- **`--market-data` flag**: The Python script reads agent-prepared JSON from `scripts/sourced_data/` — no direct API calls from the script itself
- **Manual override**: CLI flags (`--stock-price`, `--iv`, `--strike`, `--days`, `--option-type`) always take precedence over market data
- **Dependencies**: Python 3.8+, numpy, scipy, pandas

## Common Use Cases

**Use Case 1: Learn Strategy**
```
User: "Explain a covered call"

Workflow:
1. Load strategy reference (references/strategies_guide.md)
2. Explain concept, risk/reward, when to use
3. Simulate example on AAPL
4. Show P/L diagram
5. Compare to alternatives
```

**Use Case 2: Analyze Specific Trade**
```
User: "Analyze $180/$185 bull call spread on AAPL, 30 days. Also compare with 60 DTE"

Workflow:
1. Fetch AAPL stock quote & option chain from Robinhood MCP
   - `get_equity_quotes(symbols=["AAPL"])` → stock price
   - `get_option_chains(underlying_symbol="AAPL")` → chain_id, expirations
2. For the ~30 DTE expiry: get option instruments for strikes ATM±5
   - `get_option_instruments(chain_id=..., expiration_dates=..., type="call")`
   - `get_option_instruments(chain_id=..., expiration_dates=..., type="put")`
3. Get option quotes for all selected contracts
   - `get_option_quotes(instrument_ids=[...])`
4. Write market data to `scripts/sourced_data/aapl_30d.json`
5. Run `python3 scripts/black_scholes.py --market-data scripts/sourced_data/aapl_30d.json --strike 180 --days 30 --option-type both`
6. Calculate Greeks, simulate P/L, generate analysis report
7. (Optional) Repeat steps 2-6 for a ~60 DTE expiry, saving as `aapl_60d.json`, then compile a combined multi-expiration report
```

**Use Case 3: Earnings Strategy**
```
User: "Should I trade options before NVDA earnings?"

Workflow:
1. Fetch NVDA earnings date (Earnings Calendar)
2. Calculate days to earnings
3. Estimate IV percentile (if user provides IV)
4. Suggest straddle/strangle vs iron condor
5. Warn about IV crush
6. Simulate both strategies
```

**Use Case 4: Portfolio Greeks Check**
```
User: "What are my total portfolio Greeks?"

Workflow:
1. User provides current positions
2. Calculate Greeks for each position
3. Sum Greeks across portfolio
4. Assess overall exposure
5. Suggest adjustments if needed
```

## Troubleshooting

**Problem: IV not available**
- Solution: Use HV as proxy, note to user
- Ask user to provide IV from broker platform

**Problem: Negative option price**
- Solution: Check inputs (strike vs stock price)
- Deep ITM options may have numerical issues

**Problem: Greeks seem wrong**
- Solution: Verify inputs (T, sigma, r)
- Check if using annual vs daily values

**Problem: Strategy too complex**
- Solution: Break into legs, analyze separately
- Refer to references for strategy details

## Resources

**References:**
- `references/black_scholes_methodology.md` - Black-Scholes formulas, Greeks, and interpretation
- `references/strategies_guide.md` - All 17+ strategies explained (future)
- `references/greeks_explained.md` - Greeks deep dive (future)
- `references/volatility_guide.md` - HV vs IV, when to trade (future)

**Scripts:**
- `scripts/black_scholes.py` - Pricing engine and Greeks
- `scripts/fetch_oi_volume.py` - yfinance OI/volume fallback + IV Rank/Percentile
- `scripts/statistics.py` - Shared math: lognormal probs, expected move, payoff funcs, labels
- `scripts/termstructure_stats.py` - Expected move, probabilities, PC ratios, OI/volume, IV skew
- `scripts/payoff_matrix.py` - At-Expiry payoff tables for analyst-specified strategies
- `scripts/calculate_gex.py` - Gamma Exposure (GEX) calculator
- `scripts/gex_to_html.py` - GEX HTML report renderer

**External Resources:**
- Options Playbook: https://www.optionsplaybook.com/
- CBOE Education: https://www.cboe.com/education/
- Black-Scholes Calculator: Various online tools for verification

---

**Version**: 1.0
**Last Updated**: 2025-11-08
**Dependencies**: Python 3.8+, numpy, scipy, pandas, requests, yfinance
**API**: FMP API (Free tier sufficient)
