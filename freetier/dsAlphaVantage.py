import json
import os
import re
import requests

def dav(url, key):
  path = "./data/" + re.sub(r'[^\w\s]', '', url) + ".json"
  data = requests.get(f"https://alphavantage.co/query?function={url}&apikey={os.getenv('AV')}&outputsize=compact").json()

  if key in data:
    with open(path, 'w') as file:
      json.dump(data, file, indent=2)
    return json.dumps(data[key], indent=2)

  else:
    with open(path, 'r') as file:
      data = json.load(file)
    return json.dumps(data[key], indent=2)