import os
import requests
import json
from google import genai

client = genai.Client(api_key="AIzaSyDNRRmbNTQER4HzL367i7dVF-mVDDr8YdA")
mo = 'gemini-2.0-flash'

forex_data = requests.get(
    "https://www.alphavantage.co/query?function=DIGITAL_CURRENCY_DAILY&symbol=BTC&market=USD&apikey=8YUYO25GYPNE1EY8&outputsize=compact"
).json()["Time Series (Digital Currency Daily)"]

response = client.models.generate_content(
    model = mo, contents=f"""
    Analyze the following crypto price data. Give me a **prediction** of its price movement with any reasoning:
    {json.dumps(forex_data, indent=2)}
    """
)

print(response.text)