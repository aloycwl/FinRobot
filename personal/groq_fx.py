import os
import requests
import json

from groq import Groq

chat_completion = Groq(api_key="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").chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": f"""
            Analyze the following forex price data. Give me a **prediction** of it price movement with any reasoning:
            {json.dumps(requests.get(f"https://www.alphavantage.co/query?function=FX_DAILY&from_symbol=GBP&to_symbol=USD&interval=5min&apikey=8YUYO25GYPNE1EY8&outputsize=compact").
            json()["Time Series FX (Daily)"], indent=2)} """
        }
    ],
    model="deepseek-r1-distill-llama-70b",
)

print(chat_completion.choices[0].message.content)