import datetime as dt
import pandas as pd
import yfinance as yf

def pullYF(op) -> str:
  pd.set_option('display.max_rows', None)
  de = dt.datetime.now()
  ds = de - dt.timedelta(hours=12)

  df = yf.download(op, interval="5m", start=ds, end=de) 
  df.index = pd.to_datetime(df.index)
  df.index = df.index.strftime('%y-%m-%d %H:%M')
  return(df)