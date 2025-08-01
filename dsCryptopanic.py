import os
import requests as rq
from datetime import datetime as dt


def ne() -> str:

  tx = rq.get("https://cryptopanic.com/api/v1/posts/",
              params={
                  "auth_token": os.getenv('CP'),
                  "currencies": "BTC,ETH"
              }).json()

  nf = [
      f"{dt.fromisoformat(ne['created_at']).strftime('%y-%m-%d %H:%M')} {ne['title']}"
      for ne in tx.get("results", [])
  ]

  return "\n".join(nf)
