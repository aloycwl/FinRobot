import json as js
import os
import re
import requests as rq

def pullAV(url) -> str:
  path = "./data/" + re.sub(r'[^\w\s]', '', url) + ".json"
  data = rq.get(f"https://alphavantage.co/query?function={url}&apikey={os.getenv('AV')}&outputsize=compact").json()

  if 'Meta Data' in data:
    with open(path, 'w') as file: js.dump(data, file, separators=(',', ':'))
    
  else:
    with open(path, 'r') as file: data = js.load(file)
  
  return js.dumps(data, separators=(',', ':'))