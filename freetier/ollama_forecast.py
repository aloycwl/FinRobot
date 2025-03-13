import requests
import ollama
import json

print(ollama.chat(model="deepseek-r1:1.5b", messages=[{"role": "user", "content": f"""
Analyze the following stock price data . Identify trends, patterns, and potential price movements.
Based on the recent data, provide a **price prediction** for the next trading day, considering key factors like moving averages, volatility, and momentum.
Your prediction should include:
1. **Expected price range** for the next trading day.
2. **Reasons** for the prediction, including detected trends.
3. Any **potential risks or uncertainties** that could affect the forecast.
{json.dumps(requests.get(f"https://alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=HPQ&apikey=8YUYO25GYPNE1EY8&outputsize=compact").
json()["Time Series (Daily)"], indent=2)} """}])["message"]["content"])