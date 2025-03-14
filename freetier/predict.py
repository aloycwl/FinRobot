import os
import requests
import sys
from models import *
from groq import Groq
from google import genai
from datasource import pmt

selection = sys.argv[1].lower()
content = pmt(sys.argv[3])

if selection == "gemini":
  client = genai.Client(api_key=os.getenv("GK"))
  res = client.models.generate_content(
    model=gmodel[int(sys.argv[2])],
    contents=content
  )
  print(res.text)

elif selection == "groq":
  client = Groq(api_key=os.getenv("QK"))
  res = client.chat.completions.create(
    model=qmodel[int(sys.argv[2])],
    messages=[
      {"role": "system", "content": "you are a top financial trader"},
      {"role": "user", "content": content}
    ]
  )
  print(res.choices[0].message.content)

else:
  headers = {
    "Authorization": f"Bearer {os.getenv('CK')}",
    "Content-Type": "application/json",
  }
  res = requests.post(
    f"https://api.cloudflare.com/client/v4/accounts/{os.getenv('CA')}/ai/run/{cmodel[int(sys.argv[2])]}",
    headers=headers,
    json={
      "messages": [
        {"role": "system", "content": "you are top financial trader"},
        {"role": "user", "content": content},
      ]
    },
  )
  print(res.json())
