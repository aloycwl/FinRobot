import datetime
import pandas
import sys
import yfinance as yf
from dsAlphaVantage import dav

pandas.set_option('display.max_rows', None)

def pmt(op):
  txt = "Analyze following price data and give the next available **price prediction** without explanation:\n"

  if op == "1":
    return f"{txt}{dav(f'FX_DAILY&from_symbol={sys.argv[4]}&to_symbol={sys.argv[5]}')}"

  elif op == "2":
    return f"{txt}{dav(f'DIGITAL_CURRENCY_DAILY&symbol={sys.argv[4]}&market={sys.argv[5]}')}"

  elif op == "3":
    return f"{txt}{dav(f'TIME_SERIES_DAILY&symbol={sys.argv[4]}')}"

  else:
    end = datetime.datetime.now()
    sta = end - datetime.timedelta(days=7, hours=1)
    dat = yf.download([op], start=sta, end=end, interval='1h')
    return f"{txt}{dat}"