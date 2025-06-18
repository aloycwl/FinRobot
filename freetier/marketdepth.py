import requests as re

def ma() -> str:

  de = re.get("https://api.binance.com/api/v3/depth", params={"symbol":"BTCUSDT","limit":50}).json()

  tx = "Bids:\n"
  for bid in de['bids']:
    tx +=f"Price: {bid[0]}  Quantity: {bid[1]}\n"

  tx += "\nAsks:\n"
  for ask in de['asks']:
    tx += f"Price: {ask[0]}  Quantity: {ask[1]}\n"

  return tx