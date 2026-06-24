#!/usr/bin/env python3
"""
Black-Scholes Options Pricing Engine

Calculates theoretical option prices and Greeks using Black-Scholes model.

Features:
- European call and put pricing
- All Greeks (Delta, Gamma, Theta, Vega, Rho)
- Historical volatility calculation from price data
- Dividend adjustment support

Usage:
    from black_scholes import OptionPricer

    pricer = OptionPricer(
        S=180,      # Stock price
        K=185,      # Strike price
        T=30/365,   # Time to expiration (years)
        r=0.053,    # Risk-free rate
        sigma=0.25, # Volatility
        q=0.01      # Dividend yield
    )

    call_price = pricer.call_price()
    delta = pricer.call_delta()

Author: Claude Trading Skills
Version: 1.0
"""

import argparse
import json
import os

import numpy as np
import requests
from scipy.stats import norm


class OptionPricer:
    """Black-Scholes option pricer with Greeks calculation"""

    def __init__(self, S, K, T, r, sigma, q=0):
        """
        Initialize pricer with option parameters

        Parameters:
        -----------
        S : float
            Current stock price
        K : float
            Strike price
        T : float
            Time to expiration in years (e.g., 30/365 for 30 days)
        r : float
            Risk-free interest rate (annual, e.g., 0.053 for 5.3%)
        sigma : float
            Volatility (annual, e.g., 0.25 for 25%)
        q : float, optional
            Continuous dividend yield (annual, default 0)
        """
        self.S = S
        self.K = K
        self.T = T
        self.r = r
        self.sigma = sigma
        self.q = q

        # Validate inputs
        if S <= 0:
            raise ValueError("Stock price must be positive")
        if K <= 0:
            raise ValueError("Strike price must be positive")
        if T <= 0:
            raise ValueError("Time to expiration must be positive")
        if sigma <= 0:
            raise ValueError("Volatility must be positive")

    def _d1(self):
        """Calculate d1 parameter"""
        numerator = np.log(self.S / self.K) + (self.r - self.q + 0.5 * self.sigma**2) * self.T
        denominator = self.sigma * np.sqrt(self.T)
        return numerator / denominator

    def _d2(self):
        """Calculate d2 parameter"""
        return self._d1() - self.sigma * np.sqrt(self.T)

    # =========================================================================
    # Option Pricing
    # =========================================================================

    def call_price(self):
        """Calculate European call option price"""
        d1 = self._d1()
        d2 = self._d2()

        price = self.S * np.exp(-self.q * self.T) * norm.cdf(d1) - self.K * np.exp(
            -self.r * self.T
        ) * norm.cdf(d2)

        return max(0, price)  # Price cannot be negative

    def put_price(self):
        """Calculate European put option price"""
        d1 = self._d1()
        d2 = self._d2()

        price = self.K * np.exp(-self.r * self.T) * norm.cdf(-d2) - self.S * np.exp(
            -self.q * self.T
        ) * norm.cdf(-d1)

        return max(0, price)

    # =========================================================================
    # Greeks - First Order
    # =========================================================================

    def call_delta(self):
        """
        Calculate call delta

        Delta: Change in option price per $1 change in stock price
        Range: 0 to 1 for calls
        """
        d1 = self._d1()
        return np.exp(-self.q * self.T) * norm.cdf(d1)

    def put_delta(self):
        """
        Calculate put delta

        Delta: Change in option price per $1 change in stock price
        Range: -1 to 0 for puts
        """
        d1 = self._d1()
        return np.exp(-self.q * self.T) * (norm.cdf(d1) - 1)

    def vega(self):
        """
        Calculate vega (same for calls and puts)

        Vega: Change in option price per 1% change in volatility
        Always positive (options gain value when volatility increases)
        """
        d1 = self._d1()
        vega = self.S * np.exp(-self.q * self.T) * norm.pdf(d1) * np.sqrt(self.T)
        return vega / 100  # Per 1% change in volatility

    def call_theta(self):
        """
        Calculate call theta

        Theta: Change in option price per day (time decay)
        Usually negative (options lose value as time passes)
        """
        d1 = self._d1()
        d2 = self._d2()

        term1 = (
            -self.S * norm.pdf(d1) * self.sigma * np.exp(-self.q * self.T) / (2 * np.sqrt(self.T))
        )
        term2 = -self.r * self.K * np.exp(-self.r * self.T) * norm.cdf(d2)
        term3 = self.q * self.S * norm.cdf(d1) * np.exp(-self.q * self.T)

        theta_annual = term1 + term2 + term3
        return theta_annual / 365  # Convert to per-day

    def put_theta(self):
        """Calculate put theta"""
        d1 = self._d1()
        d2 = self._d2()

        term1 = (
            -self.S * norm.pdf(d1) * self.sigma * np.exp(-self.q * self.T) / (2 * np.sqrt(self.T))
        )
        term2 = self.r * self.K * np.exp(-self.r * self.T) * norm.cdf(-d2)
        term3 = -self.q * self.S * norm.cdf(-d1) * np.exp(-self.q * self.T)

        theta_annual = term1 + term2 + term3
        return theta_annual / 365

    def call_rho(self):
        """
        Calculate call rho

        Rho: Change in option price per 1% change in interest rate
        Positive for calls (calls gain value when rates increase)
        """
        d2 = self._d2()
        rho = self.K * self.T * np.exp(-self.r * self.T) * norm.cdf(d2)
        return rho / 100  # Per 1% change

    def put_rho(self):
        """
        Calculate put rho

        Rho: Change in option price per 1% change in interest rate
        Negative for puts (puts lose value when rates increase)
        """
        d2 = self._d2()
        rho = -self.K * self.T * np.exp(-self.r * self.T) * norm.cdf(-d2)
        return rho / 100

    # =========================================================================
    # Greeks - Second Order
    # =========================================================================

    def gamma(self):
        """
        Calculate gamma (same for calls and puts)

        Gamma: Change in delta per $1 change in stock price
        Shows how fast delta changes
        Highest for ATM options, lower for OTM and ITM
        """
        d1 = self._d1()
        gamma = (np.exp(-self.q * self.T) * norm.pdf(d1)) / (self.S * self.sigma * np.sqrt(self.T))
        return gamma

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def intrinsic_value(self, option_type="call"):
        """Calculate intrinsic value"""
        if option_type.lower() == "call":
            return max(0, self.S - self.K)
        else:  # put
            return max(0, self.K - self.S)

    def time_value(self, option_type="call"):
        """Calculate time value (extrinsic value)"""
        if option_type.lower() == "call":
            price = self.call_price()
        else:
            price = self.put_price()

        intrinsic = self.intrinsic_value(option_type)
        return price - intrinsic

    def moneyness(self):
        """
        Determine moneyness

        Returns: 'ITM', 'ATM', or 'OTM'
        """
        ratio = self.S / self.K

        if abs(ratio - 1.0) < 0.02:  # Within 2%
            return "ATM"
        elif ratio > 1.0:
            return "ITM (Call) / OTM (Put)"
        else:
            return "OTM (Call) / ITM (Put)"

    def get_all_greeks(self, option_type="call"):
        """
        Get all Greeks for an option

        Returns: dict with all Greeks
        """
        if option_type.lower() == "call":
            return {
                "price": self.call_price(),
                "delta": self.call_delta(),
                "gamma": self.gamma(),
                "theta": self.call_theta(),
                "vega": self.vega(),
                "rho": self.call_rho(),
                "intrinsic_value": self.intrinsic_value("call"),
                "time_value": self.time_value("call"),
            }
        else:
            return {
                "price": self.put_price(),
                "delta": self.put_delta(),
                "gamma": self.gamma(),
                "theta": self.put_theta(),
                "vega": self.vega(),
                "rho": self.put_rho(),
                "intrinsic_value": self.intrinsic_value("put"),
                "time_value": self.time_value("put"),
            }


# =============================================================================
# Historical Volatility Calculator
# =============================================================================


def calculate_historical_volatility(prices, window=30):
    """
    Calculate historical volatility from price data

    Parameters:
    -----------
    prices : array-like
        Historical prices (daily)
    window : int
        Lookback window in days (default 30)

    Returns:
    --------
    float
        Annualized historical volatility
    """
    if len(prices) < window + 1:
        raise ValueError(f"Need at least {window + 1} price points")

    # Calculate log returns
    prices = np.array(prices)
    log_returns = np.log(prices[1:] / prices[:-1])

    # Use most recent 'window' returns
    recent_returns = log_returns[-window:]

    # Annualized volatility (252 trading days)
    volatility = np.std(recent_returns) * np.sqrt(252)

    return volatility


def fetch_historical_prices_for_hv(symbol, api_key, days=90):
    """
    Fetch historical prices from FMP API for HV calculation

    Parameters:
    -----------
    symbol : str
        Stock ticker
    api_key : str
        FMP API key
    days : int
        Number of days to fetch

    Returns:
    --------
    list
        List of adjusted close prices
    """
    # Try stable endpoint first, fall back to v3
    endpoints = [
        ("https://financialmodelingprep.com/stable/historical-price-eod/full", True),
        ("https://financialmodelingprep.com/api/v3/historical-price-full", False),
    ]
    for base_url, is_stable in endpoints:
        try:
            if is_stable:
                resp = requests.get(
                    base_url,
                    params={"symbol": symbol},
                    headers={"apikey": api_key},
                    timeout=30,
                )
            else:
                resp = requests.get(
                    f"{base_url}/{symbol}",
                    headers={"apikey": api_key},
                    timeout=30,
                )
            if resp.status_code != 200:
                continue
            data = resp.json()
            historical = None
            if isinstance(data, list) and len(data) > 0:
                historical = data
            elif isinstance(data, dict) and "historical" in data:
                historical = data["historical"]
            elif isinstance(data, dict) and "historicalStockList" in data:
                for entry in data["historicalStockList"]:
                    if entry.get("symbol", "").replace("-", ".") == symbol.replace("-", "."):
                        historical = entry.get("historical", [])
                        break
            if historical:
                historical = historical[:days]
                historical = historical[::-1]  # Reverse to chronological order
                return [item.get("adjClose") or item.get("close") for item in historical]
        except Exception:  # nosec B112 - intentional fallback to next FMP endpoint
            continue

    print(f"Error fetching prices for {symbol}: all endpoints failed")
    return None


# =============================================================================
# FMP API Integration
# =============================================================================


def get_current_stock_price(symbol, api_key):
    """Fetch current stock price from FMP API (tries /stable first, falls back to v3)"""
    endpoints = [
        ("https://financialmodelingprep.com/stable/quote", True),
        (f"https://financialmodelingprep.com/api/v3/quote/{symbol}", False),
    ]
    for base_url, is_stable in endpoints:
        try:
            if is_stable:
                resp = requests.get(
                    base_url,
                    params={"symbol": symbol},
                    headers={"apikey": api_key},
                    timeout=30,
                )
            else:
                resp = requests.get(base_url, headers={"apikey": api_key}, timeout=30)
            if resp.status_code != 200:
                continue
            data = resp.json()
            if data and len(data) > 0:
                return data[0]["price"]
        except Exception:
            continue
    return None


def get_dividend_yield(symbol, api_key):
    """Fetch dividend yield from FMP API (tries /stable first, falls back to v3)"""
    endpoints = [
        ("https://financialmodelingprep.com/stable/profile", True),
        (f"https://financialmodelingprep.com/api/v3/profile/{symbol}", False),
    ]
    for base_url, is_stable in endpoints:
        try:
            if is_stable:
                resp = requests.get(
                    base_url,
                    params={"symbol": symbol},
                    headers={"apikey": api_key},
                    timeout=30,
                )
            else:
                resp = requests.get(base_url, headers={"apikey": api_key}, timeout=30)
            if resp.status_code != 200:
                continue
            data = resp.json()
            if data and len(data) > 0:
                last_div = data[0].get("lastDividend") or data[0].get("lastDiv", 0)
                price = data[0].get("price", 1)
                return (last_div / price) if price > 0 else 0
        except Exception:
            continue
    return 0


# =============================================================================
# Example Usage
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Black-Scholes Options Pricing Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/black_scholes.py --ticker AAPL\n"
            "  python scripts/black_scholes.py --market-data data.json\n"
            "  python scripts/black_scholes.py --stock-price 180 --strike 185 --days 30 --volatility 0.25\n"
            "  python scripts/black_scholes.py --stock-price 180 --strike 175 --days 30 --option-type put\n"
        ),
    )

    # Ticker / price source
    parser.add_argument("--ticker", type=str, default=None, help="Stock symbol")
    parser.add_argument("--api-key", type=str, default=None, help="FMP API key (defaults to FMP_API_KEY env var)")

    # Market data from Robinhood (JSON file created by agent)
    parser.add_argument(
        "--market-data", type=str, default=None,
        help="Path to JSON file with live market data (stock_price, options with bid/ask/iv/greeks)",
    )

    # Manual inputs
    parser.add_argument("--stock-price", type=float, default=None, help="Stock price override")
    parser.add_argument("--strike", type=float, default=185.0, help="Strike price (default: 185)")
    parser.add_argument("--days", type=int, default=30, help="Days to expiration (default: 30)")
    parser.add_argument("--volatility", type=float, default=0.25, help="Volatility as decimal (default: 0.25)")
    parser.add_argument("--iv", type=float, default=None, help="Implied volatility from market (overrides --volatility)")
    parser.add_argument("--option-type", type=str, choices=["call", "put", "both"], default="both", help="Option type to analyze (default: both)")
    parser.add_argument("--risk-free-rate", type=float, default=0.053, help="Risk-free rate (default: 0.053)")
    parser.add_argument("--dividend-yield", type=float, default=0.01, help="Dividend yield (default: 0.01)")

    # Realized volatility
    parser.add_argument(
        "--realized-vol", action="store_true", default=False,
        help="Compute realized volatility from historical closes in --market-data JSON (requires 'historical_closes' array)",
    )
    parser.add_argument(
        "--closes", type=float, nargs="*", default=None,
        help="Historical close prices for realized vol computation (comma-separated, chronological)",
    )

    args = parser.parse_args()

    # Load market data from JSON file if provided
    market_data = None
    if args.market_data:
        try:
            with open(args.market_data) as f:
                market_data = json.load(f)
            print(f"Loaded market data from {args.market_data}")
        except Exception as e:
            print(f"Warning: could not load market data: {e}")

    # Resolve API key
    api_key = args.api_key or os.environ.get("FMP_API_KEY")

    # Resolve stock price: market-data > FMP > manual default
    stock_price = args.stock_price
    if market_data and "stock_price" in market_data:
        stock_price = market_data["stock_price"]
        print(f"Using stock price from market data: ${stock_price:.2f}")

    if stock_price is None:
        # No explicit --stock-price and no market data
        stock_price = 180.0  # fallback default

    # Resolve volatility: --iv > market data IV > --volatility
    volatility = args.volatility
    if args.iv is not None:
        volatility = args.iv
    elif market_data and "options" in market_data and len(market_data["options"]) > 0:
        # Use IV from first option matching our strike
        target_strike = args.strike
        for opt in market_data["options"]:
            if abs(opt.get("strike", 0) - target_strike) < 0.01:
                if "iv" in opt and opt["iv"] is not None and opt["iv"] > 0:
                    volatility = opt["iv"]
                    print(f"Using market IV for strike ${target_strike:.0f}: {volatility * 100:.1f}%")
                    break

    ticker = args.ticker
    if ticker is None and market_data and "ticker" in market_data:
        ticker = market_data["ticker"]

    # FMP fallback for stock price if no market data provided
    if ticker and api_key and stock_price == 180.0 and not market_data and args.stock_price is None:
        live_price = get_current_stock_price(ticker, api_key)
        if live_price:
            stock_price = live_price
            print(f"Fetched live price for {ticker}: ${stock_price:.2f}")

    strike_price = args.strike
    days_to_expiration = args.days
    time_to_expiration = days_to_expiration / 365
    risk_free_rate = args.risk_free_rate
    dividend_yield = args.dividend_yield

    print("\n" + "=" * 70)
    title = f"BLACK-SCHOLES OPTIONS PRICER{f' - {ticker}' if ticker else ''}"
    print(title)
    print("=" * 70)

    print("\nInput Parameters:")
    print(f"  Stock Price: ${stock_price:.2f}")
    print(f"  Strike Price: ${strike_price:.2f}")
    print(f"  Days to Expiration: {days_to_expiration}")
    print(f"  Volatility: {volatility * 100:.1f}%")
    print(f"  Risk-Free Rate: {risk_free_rate * 100:.2f}%")
    print(f"  Dividend Yield: {dividend_yield * 100:.1f}%")

    # Create pricer
    pricer = OptionPricer(
        S=stock_price,
        K=strike_price,
        T=time_to_expiration,
        r=risk_free_rate,
        sigma=volatility,
        q=dividend_yield,
    )

    # Build market option lookup for comparison
    market_lookup = {}
    if market_data and "options" in market_data:
        for opt in market_data["options"]:
            key = (opt.get("strike"), opt.get("type", "").lower())
            market_lookup[key] = opt

    # Analyze requested option type(s)
    option_types = ["call", "put"] if args.option_type == "both" else [args.option_type]

    for opt_type in option_types:
        print(f"\n{'=' * 70}")
        print(f"{opt_type.upper()} OPTION")
        print("=" * 70)

        greeks = pricer.get_all_greeks(opt_type)
        print(f"  Theoretical Price: ${greeks['price']:.2f}")

        # Show market price if available
        mkey = (strike_price, opt_type)
        if mkey in market_lookup:
            m = market_lookup[mkey]
            bid = m.get("bid")
            ask = m.get("ask")
            last = m.get("last")
            if bid is not None and ask is not None:
                print(f"  Market Price:       ${bid:.2f} x ${ask:.2f} (bid/ask)")
            elif last is not None:
                print(f"  Market Price:       ${last:.2f} (last)")

        print(f"  Intrinsic Value: ${greeks['intrinsic_value']:.2f}")
        print(f"  Time Value: ${greeks['time_value']:.2f}")
        print("\n  Greeks:")
        print(f"    Delta: {greeks['delta']:.4f} (${greeks['delta'] * 100:.2f} per $1 move)")
        print(f"    Gamma: {greeks['gamma']:.4f} (delta changes by {greeks['gamma']:.4f})")
        print(f"    Theta: ${greeks['theta']:.2f}/day (loses ${abs(greeks['theta']):.2f} per day)")
        print(f"    Vega: ${greeks['vega']:.2f} per 1% IV (gains ${greeks['vega']:.2f} if IV +1%)")

        rho_sign = "gains" if opt_type == "call" else "loses"
        print(f"    Rho: ${greeks['rho']:.2f} per 1% rate ({rho_sign} ${abs(greeks['rho']):.2f} if rate +1%)")

        # Show market Greeks if available
        if mkey in market_lookup:
            m = market_lookup[mkey]
            mg = {k: m.get(k) for k in ("delta", "gamma", "theta", "vega")}
            if any(v is not None for v in mg.values()):
                print("\n  Market Greeks:")
                if mg["delta"] is not None:
                    print(f"    Delta: {mg['delta']:.4f}")
                if mg["gamma"] is not None:
                    print(f"    Gamma: {mg['gamma']:.4f}")
                if mg["theta"] is not None:
                    print(f"    Theta: ${mg['theta']:.2f}/day")
                if mg["vega"] is not None:
                    print(f"    Vega: ${mg['vega']:.2f} per 1% IV")

    # Moneyness
    print(f"\n{'=' * 70}")
    print(f"Moneyness: {pricer.moneyness()}")
    print("=" * 70 + "\n")

    # Realized Volatility (from market data JSON or --closes)
    if args.realized_vol or args.closes is not None:
        closes = None
        if args.closes is not None and len(args.closes) > 0:
            closes = list(args.closes)
        elif market_data and "historical_closes" in market_data:
            closes = market_data["historical_closes"]
        else:
            print("\nNo historical closes available. Include 'historical_closes' array in --market-data JSON or pass --closes.")

        if closes and len(closes) > 20:
            prices = np.array(closes, dtype=float)
            log_returns = np.diff(np.log(prices))

            windows = [(10, "RV-10"), (20, "RV-20"), (30, "RV-30"), (60, "RV-60")]
            results = {}
            for win, label in windows:
                if len(log_returns) >= win:
                    results[label] = np.std(log_returns[-win:]) * np.sqrt(252)
                else:
                    results[label] = None

            # Longer-term: use max available >=90
            if len(log_returns) >= 90:
                results["RV-90"] = np.std(log_returns[-90:]) * np.sqrt(252)
            else:
                results["RV-Long"] = np.std(log_returns) * np.sqrt(252)

            print("\nRealized Volatility (from historical closes):")
            print("-" * 70)
            print(f"  {'Period':<10} {'RV':>8} {'IV/RV':>10}")
            print(f"  {'-'*8:<10} {'-'*6:>8} {'-'*8:>10}")
            for label in ["RV-10", "RV-20", "RV-30", "RV-60", "RV-Long"]:
                if label in results and results[label] is not None:
                    rv = results[label] * 100
                    ratio = volatility / results[label]
                    arrow = "RV > IV" if ratio < 0.9 else ("RV < IV" if ratio > 1.1 else "RV ~ IV")
                    print(f"  {label:<10} {rv:>6.1f}%  {ratio:>7.2f}x  ({arrow})")
            print(f"\n  Current IV (input): {volatility * 100:.1f}%")
            print(f"  Data points: {len(closes)} closes, {len(log_returns)} daily returns")
        elif closes:
            print(f"\n  Need >20 close prices (got {len(closes)}). Skipping realized vol.")
    else:
        # Legacy path: simulated HV
        pass

    # Historical Volatility
    hv = None
    if ticker and api_key:
        print("Historical Volatility:")
        print("-" * 70)
        prices = fetch_historical_prices_for_hv(ticker, api_key, days=90)
        if prices:
            hv = calculate_historical_volatility(prices, window=30)
            print(f"  30-Day HV for {ticker}: {hv * 100:.2f}%")
        else:
            print(f"  Could not fetch historical data for {ticker}")
    else:
        print("Historical Volatility (simulated):")
        print("-" * 70)
        np.random.seed(42)
        simulated_prices = [stock_price * np.exp(np.sum(np.random.randn(i) * 0.01)) for i in range(90)]
        hv = calculate_historical_volatility(simulated_prices, window=30)
        print(f"  30-Day Historical Volatility: {hv * 100:.2f}%")

    if hv is not None:
        print(f"  Implied Volatility (input): {volatility * 100:.1f}%")
        if hv < volatility:
            print("  => IV > HV: Options may be expensive (consider selling premium)")
        elif hv > volatility:
            print("  => IV < HV: Options may be cheap (consider buying)")
        else:
            print("  => IV ~= HV: Options fairly priced")

    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    main()
