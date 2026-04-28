from __future__ import annotations

import pandas as pd


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gains = delta.where(delta > 0, 0.0)
    losses = -delta.where(delta < 0, 0.0)
    rs = gains.rolling(period).mean() / losses.rolling(period).mean()
    return 100 - (100 / (1 + rs))


def enrich_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    df = frame.copy()
    df["EMA_200"] = df["close"].ewm(span=200, adjust=True).mean()
    df["EMA_50"] = df["close"].ewm(span=50, adjust=True).mean()
    df["SMA_20"] = df["close"].rolling(window=20).mean()
    df["STD_20"] = df["close"].rolling(window=20).std()
    df["Upper_Band"] = df["SMA_20"] + (df["STD_20"] * 2)
    df["Lower_Band"] = df["SMA_20"] - (df["STD_20"] * 2)
    df["Middle_Band"] = df["SMA_20"]
    df["RSI_14"] = rsi(df["close"])
    df["MACD"] = df["close"].ewm(span=12, adjust=True).mean() - df["close"].ewm(span=26, adjust=True).mean()
    df["Signal_Line"] = df["MACD"].ewm(span=9, adjust=True).mean()
    df["MACD_Histogram"] = df["MACD"] - df["Signal_Line"]
    df["Volume_SMA_20"] = df["volume"].rolling(window=20).mean()
    low14 = df["low"].rolling(window=14).min()
    df["%K"] = 100 * ((df["close"] - low14) / (df["high"].rolling(window=14).max() - low14))
    df["%D"] = df["%K"].rolling(window=3).mean()
    df["Support"] = df["low"].rolling(window=20).min()
    df["Resistance"] = df["high"].rolling(window=20).max()
    return df
