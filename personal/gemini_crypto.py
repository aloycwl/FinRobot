import requests
import json
from google import genai

print(genai.Client(api_key="AIzaSyDNRRmbNTQER4HzL367i7dVF-mVDDr8YdA").models.generate_content(
    model = 'gemini-2.0-flash-lite', contents=f"""
    Analyze the following crypto price data. Give me a **prediction** of its price movement for tomorrow without any reasoning:
    {json.dumps(requests.get(
    "https://alphavantage.co/query?function=DIGITAL_CURRENCY_DAILY&symbol=BTC&market=USD&apikey=8YUYO25GYPNE1EY8&outputsize=compact"
    ).json()["Time Series (Digital Currency Daily)"], indent=2)}
    """
).text)