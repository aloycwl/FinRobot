import json
import os
import requests
import re

def fetch_data(url, expected_key):
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

def analyse(query):
  return f"Analyze following {query} price data. Give tomorrow's **price prediction**:\n"

def get_content(option):
  if option == 1:
    return f"""{analyse('forex')}{fetch_data("FX_DAILY&from_symbol=GBP&to_symbol=USD", "Time Series FX (Daily)")}"""
  elif option == 2:
    return f"""{analyse('cryptocurrency')}{fetch_data("DIGITAL_CURRENCY_DAILY&symbol=BTC&market=USD", "Time Series (Digital Currency Daily)")}"""
  elif option == 3:
    return f"""{analyse('stock')}{fetch_data("TIME_SERIES_DAILY&symbol=NVDA", "Time Series (Daily)")}"""
  else:
    return "Share a short trading tip"