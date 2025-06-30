import requests as re

def ma() -> str:
    b = re.get("https://www.okx.com/api/v5/market/books",
                     params={
                         "instId": "BTC-USDT",
                         "sz": "50"
                     }).json()['data'][0]

    t = "Bids:\n"
    for price, qty, *others in b['bids']:
        t += f"Price: {price}  Quantity: {qty}\n"

    t += "\nAsks:\n"
    for price, qty, *others in b['asks']:
        t += f"Price: {price}  Quantity: {qty}\n"

    return t