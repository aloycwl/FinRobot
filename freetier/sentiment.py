import requests as re

def se() -> str:

  dat = re.get("https://api.alternative.me/fng/?limit=10&date_format=us").json()

  txt = "date,fng_value,fng_classification\n"
  for itm in dat['data']:
    txt += f"{itm['timestamp']},{itm['value']},{itm['value_classification']}\n"

  return(txt)