import json as js
import os
import re
import requests as rq

def pullAV(url) -> str:
  
  pa = "./data/" + re.sub(r'[^\w\s]', '', url) + ".json"
  da = rq.get(f"https://alphavantage.co/query?function={url}&apikey={os.getenv('AV')}&outputsize=compact").json()

  if 'Meta Data' in da:
    with open(pa, 'w') as file: js.dump(da, file, separators=(',', ':'))
    
  else:
    with open(pa, 'r') as file: da = js.load(file)
  
  return js.dumps(da, separators=(',', ':'))