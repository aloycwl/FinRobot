import requests as re

def ma() -> str:

  de = re.get("https://api.binance.com/api/v3/depth", params={"symbol":"BTCUSDT","limit":50}).json()

  rs = "Bids:\n"
  for bid in de['bids']:
    rs +=f"Price: {bid[0]}  Quantity: {bid[1]}\n"

  rs += "\nAsks:\n"
  for ask in de['asks']:
    rs += f"Price: {ask[0]}  Quantity: {ask[1]}\n"

  return rs