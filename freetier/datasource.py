import datetime
import pandas as pd
import sys
import yfinance as yf
from dsAlphaVantage import dav

pd.set_option('display.max_rows', None)

def pmt(op):
  txt = (
    "Analyze the following high-frequency price data (OHLC) and "
    "predict the next available price for the next 5-10 minutes.\n"
  )

  if op == "1":
    return f"{txt}{dav(f'FX_DAILY&from_symbol={sys.argv[4]}&to_symbol={sys.argv[5]}')}"

  elif op == "2":
    return f"{txt}{dav(f'DIGITAL_CURRENCY_DAILY&symbol={sys.argv[4]}&market={sys.argv[5]}')}"

  elif op == "3":
    return f"{txt}{dav(f'TIME_SERIES_DAILY&symbol={sys.argv[4]}')}"

  else:
    df = yf.download(op, interval="1m", period="1d")[['Close']] 
    df.index = pd.to_datetime(df.index)
    l2 = df[df.index > (df.index[-1] - pd.Timedelta(hours=2))]
    l2.index = l2.index.strftime('%y-%m-%d %H:%M')

    return f"{txt}{l2}"

# print(pmt('EURJPY=X'))