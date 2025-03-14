import json
import os
import requests

# Retrieve API key with fallback
api_key = os.getenv("AV", "default_api_key")
qs = f"&apikey={api_key}&outputsize=compact"

# Function to fetch data and handle errors
def fetch_data(url, expected_key):
    try:
        response = requests.get(url)
        data = response.json()
        
        # Debug: Print full API response if key is missing
        if expected_key not in data:
            print(f"Warning: Expected key '{expected_key}' not found. Full response:")
            print(json.dumps(data, indent=2))
            return "Error: Data not available."

        return json.dumps(data[expected_key], indent=2)
    
    except requests.RequestException as e:
        print(f"API request failed: {e}")
        return "Error: API request failed."
    except json.JSONDecodeError:
        print("Error: Failed to parse JSON response.")
        return "Error: Invalid JSON response."

# Fetch data from Alpha Vantage API
forex_data = fetch_data(
    f"https://www.alphavantage.co/query?function=FX_DAILY&from_symbol=GBP&to_symbol=USD{qs}",
    "Time Series FX (Daily)"
)

crypto_data = fetch_data(
    f"https://www.alphavantage.co/query?function=DIGITAL_CURRENCY_DAILY&symbol=BTC&market=USD{qs}",
    "Time Series (Digital Currency Daily)"
)

stock_data = fetch_data(
    f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=NVDA{qs}",
    "Time Series (Daily)"
)

# Content list
content = [
    "Share a short trading tip",  # 0
    f"""Analyze the following forex price data. Give a **price prediction** for tomorrow:\n{forex_data}""",  # 1
    f"""Analyze the following cryptocurrency price data. Give a **price prediction** for tomorrow:\n{crypto_data}""",  # 2
    f"""Analyze the following stock price data. Give a **price prediction** for tomorrow:\n{stock_data}""",  # 3
]