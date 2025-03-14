import datetime
import json
import os
import pandas
import re
import requests
import yfinance as yf

pandas.set_option('display.max_rows', None)

def get(url, expected_key):
  path = "./data/" + re.sub(r'[^\w\s]', '', url) + ".json"
  data = requests.get(f"https://alphavantage.co/query?function={url}&apikey={os.getenv('AV')}&outputsize=compact").json()

  if expected_key in data:
    with open(path, 'w') as file:
      json.dump(data, file, indent=2)
    return json.dumps(data[expected_key], indent=2)

  else:
    with open(path, 'r') as file:
      data = json.load(file)
    if expected_key in data:
      return json.dumps(data[expected_key], indent=2)

txt = f"Analyze following price data and give the next available **price prediction**:\n"

def pmt(op):
  if op == "1":
    return f"""{txt}{get('FX_DAILY&from_symbol=GBP&to_symbol=USD', 'Time Series FX (Daily)')}"""
  elif op == "2":
    return f"""{txt}{get('DIGITAL_CURRENCY_DAILY&symbol=BTC&market=USD', 'Time Series (Digital Currency Daily)')}"""
  elif op == "3":
    return f"""{txt}{get('TIME_SERIES_DAILY&symbol=NVDA', 'Time Series (Daily)')}"""
  else:
    dateE = datetime.datetime.now()
    dateS = dateE - datetime.timedelta(days=7, hours=1)
    data = yf.download([op], start=dateS, end=dateE, interval='1h')
    return f"""{txt}{data}"""