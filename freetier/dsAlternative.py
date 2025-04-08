import requests as re

def se() -> str:

  da = re.get("https://api.alternative.me/fng/?limit=10&date_format=us").json()

  tx = "date,fng_value,fng_classification\n"
  for itm in da['data']:
    tx += f"{itm['timestamp']},{itm['value']},{itm['value_classification']}\n"

  return tx