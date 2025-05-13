import requests as re
import pandas as pd
import time

def pullBinance() -> str:
    df = pd.DataFrame(
      re.get("https://api.binance.com/api/v3/klines", params={
      "symbol": "BTCUSDT", "interval": "5m", "limit": 50}).json(), 
      columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "num_trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ])
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('date', inplace=True)
    return df[["open", "high", "low", "close", "volume"]].astype(float)