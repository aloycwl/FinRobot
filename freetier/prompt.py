import json
import requests

content = ["share a short trading tip", #0
f"""Analyze the following forex price data. Give a **price prediction** for tomorrow:
{json.dumps(requests.get("https://www.alphavantage.co/query?function=FX_DAILY&from_symbol=GBP&to_symbol=USD&interval=5min&apikey=8YUYO25GYPNE1EY8&outputsize=compact"
).json()["Time Series FX (Daily)"], indent=2)}""", #1
f"""Analyze the following cryptocurrency price data. Give a **price prediction** for tomorrow:
{json.dumps(requests.get(f"https://www.alphavantage.co/query?function=DIGITAL_CURRENCY_DAILY&symbol=BTC&market=USD&apikey=8YUYO25GYPNE1EY8&outputsize=compact"
).json()["Time Series (Digital Currency Daily)"], indent=2)}""", #2
f"""Analyze the following stock price data. Give a **price prediction** for tomorrow:
{json.dumps(requests.get(f"https://alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=NVDA&apikey=8YUYO25GYPNE1EY8&outputsize=compact"
).json()["Time Series (Daily)"], indent=2)}"""] #3