from __future__ import annotations

import os
from datetime import datetime
import pandas as pd
import requests
import logging

from .config import settings

logger = logging.getLogger("data_sources")

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    logger.info("MetaTrader5 not available, using OKX as primary data source")


def fetch_mt5_candles(limit: int = 1000) -> pd.DataFrame:
    """Fetch historical OHLC candles from MetaTrader 5 for XAUUSD"""
    if not MT5_AVAILABLE:
        return fetch_okx_candles(limit)
    if not mt5.initialize():
        logger.error(f"MT5 initialize failed: {mt5.last_error()}")
        return fetch_okx_candles(limit)
        
    # Login with configured credentials
    login_ok = mt5.login(
        login=settings.mt5_login,
        password=settings.mt5_password,
        server=settings.mt5_server
    )
    
    if not login_ok:
        logger.error(f"MT5 login failed: {mt5.last_error()}")
        mt5.shutdown()
        return fetch_okx_candles(limit)
    
    # Fetch 1 minute candles
    rates = mt5.copy_rates_from_pos(settings.mt5_symbol, mt5.TIMEFRAME_M1, 0, limit)
    mt5.shutdown()
    
    if rates is None:
        logger.error(f"Failed to fetch MT5 rates: {mt5.last_error()}")
        return fetch_okx_candles(limit)
        
    df = pd.DataFrame(rates)
    df['date'] = pd.to_datetime(df['time'], unit='s', utc=True)
    df = df.set_index('date')
    
    # Normalize column names to match OKX format
    df.rename(columns={'tick_volume': 'volume'}, inplace=True)
    
    # Return same format as OKX
    return df[["open", "high", "low", "close", "volume"]].sort_index()


from .historical_cache import cache

def fetch_candles(limit: int = 1000) -> pd.DataFrame:
    """Universal candle fetcher with cache - prioritizes local historical data"""
    symbol = settings.okx_symbol
    
    # FIRST: Load from local CSV data (always use this first for backtesting)
    csv_path = "/home/openclaw/FinRobot/data/XAUUSD1.csv"
    if os.path.exists(csv_path):
        df = pd.read_csv(
            csv_path,
            sep="\t",
            header=None,
            names=["time", "open", "high", "low", "close", "volume"],
            parse_dates=["time"]
        )
        df = df.set_index("time")
        df = df.sort_index().tail(limit)
        logger.info(f"Loaded {len(df)} bars from local historical data")
        return df
    
    # Then try cache
    cached = cache.get_candles(symbol, limit)
    if cached is not None and len(cached) >= limit * 0.9:
        logger.debug(f"Returning {len(cached)} cached candles")
        return cached
    
    # Fetch fresh data only if local data not available
    df = None
    if MT5_AVAILABLE and settings.mt5_login and settings.mt5_password:
        df = fetch_mt5_candles(limit)
    
    if df is None or len(df) == 0:
        df = fetch_okx_candles(limit)
    
    # Cache the result
    if df is not None and len(df) > 0:
        cache.insert_candles(df, symbol)
        logger.info(f"Cached {len(df)} new candles, total now: {cache.count_candles(symbol)}")
    
    # Always return at least an empty dataframe with correct columns
    if df is None or len(df) == 0:
        logger.warning(f"Returning empty dataframe for {symbol}")
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    
    return df


def fetch_okx_candles(limit: int = 600) -> pd.DataFrame:
    response = requests.get(
        "https://www.okx.com/api/v5/market/candles",
        params={"instId": settings.okx_symbol, "bar": settings.okx_bar, "limit": str(limit)},
        timeout=20,
    )
    response.raise_for_status()
    rows = response.json()["data"]
    frame = pd.DataFrame(
        rows,
        columns=[
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "currency_volume",
            "num_trades",
            "unknown",
        ],
    )
    frame["date"] = pd.to_datetime(frame["timestamp"].astype(int), unit="ms", utc=True)
    frame = frame.set_index("date")
    for column in ["open", "high", "low", "close", "volume"]:
        frame[column] = frame[column].astype(float)
    return frame[["open", "high", "low", "close", "volume"]].sort_index()


def fetch_news() -> str:
    if not settings.cryptopanic_token:
        return "No CryptoPanic token configured (CP)."
    response = requests.get(
        "https://cryptopanic.com/api/v1/posts/",
        params={"auth_token": settings.cryptopanic_token, "currencies": "BTC,ETH"},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    lines = []
    for item in payload.get("results", []):
        created_at = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
        lines.append(f"{created_at:%y-%m-%d %H:%M} {item['title']}")
    return "\n".join(lines)


def fetch_market_depth(size: int = 50) -> str:
    response = requests.get(
        "https://www.okx.com/api/v5/market/books",
        params={"instId": settings.okx_symbol, "sz": str(size)},
        timeout=20,
    )
    response.raise_for_status()
    depth = response.json()["data"][0]
    out = ["Bids:"]
    for price, qty, *_ in depth["bids"]:
        out.append(f"Price: {price} Quantity: {qty}")
    out.append("\nAsks:")
    for price, qty, *_ in depth["asks"]:
        out.append(f"Price: {price} Quantity: {qty}")
    return "\n".join(out)


def fetch_fear_greed(limit: int = 10) -> str:
    response = requests.get(
        "https://api.alternative.me/fng/",
        params={"limit": str(limit), "date_format": "us"},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    lines = ["date,fng_value,fng_classification"]
    for row in payload["data"]:
        lines.append(f"{row['timestamp']},{row['value']},{row['value_classification']}")
    return "\n".join(lines)
