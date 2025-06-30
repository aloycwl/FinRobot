import requests as re
import pandas as pd


def pullOkx() -> pd.DataFrame:

    df = pd.DataFrame(re.get("https://www.okx.com/api/v5/market/candles",
                             params={
                                 "instId": "BTC-USDT",
                                 "bar": "5m",
                                 "limit": "50"
                             }).json()['data'],
                      columns=[
                          "timestamp", "open", "high", "low", "close",
                          "volume", "currency_volume", "num_trades", "unknown"
                      ])

    df['date'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
    df.set_index('date', inplace=True)

    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)

    df.drop(columns=['unknown'], inplace=True)

    return df[["open", "high", "low", "close", "volume"]]