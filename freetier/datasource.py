import datetime
import pandas
import yfinance as yf
from dsAlphaVantage import dav

pandas.set_option('display.max_rows', None)

def pmt(op):
  if op == "1":
    return f"""{txt}{dav('FX_DAILY&from_symbol=USD&to_symbol=CAD', 'Time Series FX (Daily)')}"""
  elif op == "2":
    return f"""{txt}{dav('DIGITAL_CURRENCY_DAILY&symbol=BTC&market=USD', 'Time Series (Digital Currency Daily)')}"""
  elif op == "3":
    return f"""{txt}{dav('TIME_SERIES_DAILY&symbol=MSFT', 'Time Series (Daily)')}"""
  else:
    end = datetime.datetime.now()
    sta = end - datetime.timedelta(days=7, hours=1)
    dat = yf.download([op], start=sta, end=end, interval='1h')
    return f"""Analyze following price data and give the next available **price prediction** without explanation:\n{dat}"""