import os
import datetime
import json
try:
    import yfinance as yf
except ImportError:
    yf = None  # yfinance not available, price fetching will fallback
import feedparser
import requests
import numpy as np


# Simple mapping of common Indian companies to NSE ticker symbols
COMPANY_TICKER_MAP = {
    "reliance": "RELIANCE.NS",
    "tcs": "TCS.NS",
    "infy": "INFY.NS",
    "hdfc": "HDFCBANK.NS",
    "itc": "ITC.NS",
    "sbin": "SBIN.NS",
    "icicibank": "ICICIBANK.NS",
    "adani": "ADANIENT.NS",
}

def _resolve_symbol(query: str) -> str:
    """Return a NSE ticker symbol for the given query.
    If the query matches a key in ``COMPANY_TICKER_MAP`` the mapped value is used.
    Returns symbol without trailing '.NS' for NSE API usage.
    """
    key = query.strip().lower()
    # Use mapping if available, otherwise assume query is the ticker symbol.
    ticker = COMPANY_TICKER_MAP.get(key, query.upper())
    # Ensure ticker does not contain the '.NS' suffix for NSE API.
    if ticker.endswith('.NS'):
        ticker = ticker.replace('.NS', '')
    return ticker

def _fetch_google_finance_price(symbol: str) -> float:
    """Helper to fetch price from Google Finance."""
    try:
        url = f"https://www.google.com/finance/quote/{symbol}:NSE"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            import re
            match = re.search(r'data-last-price="([^"]+)"', response.text)
            if match:
                return float(match.group(1))
    except Exception:
        pass
    return None

def get_price(symbol: str) -> float:
    """Fetch the latest price using NSE API, Google Finance, or yfinance."""
    # 1. Try NSE API
    try:
        session = requests.Session()
        session.get('https://www.nseindia.com', headers={'User-Agent': 'Mozilla/5.0'})
        url = f'https://www.nseindia.com/api/quote-equity?symbol={symbol}'
        headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json', 'Referer': 'https://www.nseindia.com/'}
        resp = session.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            price = resp.json().get('priceInfo', {}).get('lastPrice')
            if price: return float(price)
    except Exception:
        pass
    
    # 2. Try Google Finance
    price = _fetch_google_finance_price(symbol)
    if price: return price

    # 3. Fallback to yfinance if available
    if yf is not None:
        try:
            ticker = yf.Ticker(f"{symbol}.NS")
            return ticker.fast_info.get('last_price')
        except Exception:
            pass
    return None

def get_history(symbol: str, days: int = 30):
    """Return a list of historical daily close prices for the last *days*.
    Each entry is a ``{"date": "YYYY‑MM‑DD", "close": float}`` dict.
    """
    if yf is not None:
        try:
            ticker = yf.Ticker(f"{symbol}.NS")
            hist = ticker.history(period=f"{days}d")
            result = []
            for idx, row in hist.iterrows():
                result.append({"date": idx.strftime("%Y-%m-%d"), "close": round(row["Close"], 2)})
            return result
        except Exception:
            pass
    return []


def get_news(query: str, max_items: int = 5):
    """Fetch the latest news headlines from Google News RSS for *query*.
    Returns a list of ``{"title": str, "link": str}`` dictionaries.
    """
    try:
        rss_url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}"
        feed = feedparser.parse(rss_url)
        items = []
        for entry in feed.entries[:max_items]:
            items.append({"title": entry.title, "link": entry.link})
        return items
    except Exception:
        return []

def get_one_year_history(symbol: str):
    """Return historical daily close prices for the past 1 year (approx. 252 trading days)."""
    # Use yfinance which can fetch by period string '1y' for better accuracy
    if yf is not None:
        try:
            ticker = yf.Ticker(f"{symbol}.NS")
            hist = ticker.history(period='1y')
            result = []
            for idx, row in hist.iterrows():
                result.append({"date": idx.strftime("%Y-%m-%d"), "close": round(row["Close"], 2)})
            return result
        except Exception:
            pass
    # Fallback to get_history with 365 days if yfinance unavailable
    return get_history(symbol, days=365)

def analyze_company(query: str):
    """Collect price, historical trend, news and simulate next day price using geometric Brownian motion.
    Returns a dictionary ready for JSON response.
    """
    symbol = _resolve_symbol(query)
    price = get_price(symbol)
    history = get_history(symbol, days=30)
    news = get_news(query)

    # Compute simple price change % over the period if data available
    change_pct = None
    if history:
        first = history[0]["close"]
        last = history[-1]["close"]
        if first:
            change_pct = round(((last - first) / first) * 100, 2)

    analysis_parts = []
    if price is not None:
        analysis_parts.append(f"Current price of {symbol} is ₹{price:.2f}.")
    if change_pct is not None:
        direction = "up" if change_pct > 0 else "down"
        analysis_parts.append(f"It has moved {direction} {abs(change_pct)}% over the last 30 days.")
    if news:
        analysis_parts.append(f"Recent headlines mention: \"{news[0]['title']}\".")
    analysis = " ".join(analysis_parts) if analysis_parts else "No data available."

    # Simulation using geometric Brownian motion based on real historical data
    S0 = price if price is not None else 1000
    # Compute annualized drift (mu) and volatility (sigma) from price history if available
    if history and len(history) >= 2:
        # Calculate daily log returns
        closes = [day["close"] for day in history]
        returns = np.diff(np.log(closes))
        daily_mu = np.mean(returns)
        daily_sigma = np.std(returns)
        mu = daily_mu * 252  # annualize drift
        sigma = daily_sigma * np.sqrt(252)  # annualize volatility
    else:
        mu = 0.12
        sigma = 0.25
    dt = 1/252
    epsilon = np.random.normal()
    S1 = S0 * np.exp((mu - 0.5 * sigma ** 2) * dt + sigma * np.sqrt(dt) * epsilon)

    simulation = {
        "next_price": round(S1, 2),
        "mu": mu,
        "sigma": sigma,
        "dt": dt,
        "epsilon": epsilon,
    }

    return {
        "symbol": symbol,
        "price": price,
        "price_change_pct": change_pct,
        "history": history,
        "news": news,
        "analysis": analysis,
        "simulation": simulation,
    }
