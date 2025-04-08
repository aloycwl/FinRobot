import os
import requests as rq
from datetime import datetime as dt

def ne() -> str:
  tx = rq.get("https://cryptopanic.com/api/v1/posts/", params={
    "auth_token":os.getenv('CP'),
    "currencies":"BTC,ETH"
  }).json()

  nf = [
    f"{dt.strptime(ne['created_at'], '%Y-%m-%dT%H:%M:%SZ').strftime('%y-%m-%d %H:%M')} {ne['title']}"
    for ne in tx.get("results", [])
  ]

  tx = "\n".join(nf)

  return tx