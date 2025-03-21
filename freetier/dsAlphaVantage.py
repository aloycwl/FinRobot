import json
import os
import re
import requests

def dav(url):
  path = "./data/" + re.sub(r'[^\w\s]', '', url) + ".json"
  data = requests.get(f"https://alphavantage.co/query?function={url}&apikey={os.getenv('AV')}&outputsize=compact").json()

  if 'Meta Data' in data:
    with open(path, 'w') as file: json.dump(data, file, separators=(',', ':'))
    
  else:
    with open(path, 'r') as file: data = json.load(file)
  
  return json.dumps(data, separators=(',', ':'))