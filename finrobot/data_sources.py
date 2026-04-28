from __future__ import annotations

from datetime import datetime
import pandas as pd
import requests

from .config import settings


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
