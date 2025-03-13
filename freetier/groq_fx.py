import requests
import json
from groq import Groq

print(Groq(api_key="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").chat.completions.create(
    model="deepseek-r1-distill-llama-70b",messages=[{"role": "user","content": f"""
    Analyze the following forex price data. Give me a **prediction** of its price movement for tomorrow without any reasoning:
    {json.dumps(requests.get(f"https://www.alphavantage.co/query?function=FX_DAILY&from_symbol=GBP&to_symbol=USD&interval=5min&apikey=8YUYO25GYPNE1EY8&outputsize=compact").
    json()["Time Series FX (Daily)"], indent=2)} """}]).choices[0].message.content)