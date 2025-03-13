import requests
import json
from google import genai

print(genai.Client(api_key="AIzaSyDNRRmbNTQER4HzL367i7dVF-mVDDr8YdA").models.generate_content(
    model = 'gemini-2.0-flash-lite', contents=f"""
    Analyze the following stock price data . Identify trends, patterns, and potential price movements.
    Based on the recent data, provide a **price prediction** for the next trading day, considering key factors like moving averages, volatility, and momentum.
    Your prediction should include:
    1. **Expected price range** for the next trading day.
    {json.dumps(requests.get(
    "https://alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=TSLA&apikey=8YUYO25GYPNE1EY8&outputsize=compact"
    ).json()["Time Series (Daily)"], indent=2)}
    """
).text)