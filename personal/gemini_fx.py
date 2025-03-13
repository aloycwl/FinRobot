import requests
import json
from google import genai

print(genai.Client(api_key="AIzaSyDNRRmbNTQER4HzL367i7dVF-mVDDr8YdA").models.generate_content(
    model = 'gemini-2.0-flash-lite', contents=f"""
    Analyze the following forex price data. Give me a **prediction** of its price movement for tomorrow without any reasoning:
    {json.dumps(requests.get(
    "https://www.alphavantage.co/query?function=FX_DAILY&from_symbol=GBP&to_symbol=USD&interval=5min&apikey=8YUYO25GYPNE1EY8&outputsize=compact"
    ).json()["Time Series FX (Daily)"], indent=2)}
    """
).text)