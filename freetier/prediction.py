import os
import requests
import sys
from models import *
from groq import Groq
from google import genai
from prompt import get_content

selection = sys.argv[1].lower()

if selection == "gemini":
  client = genai.Client(api_key=os.getenv("GK"))
  res = client.models.generate_content(
    model=gmodel[int(sys.argv[2])],
    contents=get_content(int(sys.argv[3]))
  )
  print(res.text)

elif selection == "groq":
  groq_client = Groq(api_key=os.getenv("QK"))
  model = qmodel[int(sys.argv[2])]
  content = get_content(int(sys.argv[3]))

  res = groq_client.chat.completions.create(
    model=model,
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
        {"role": "user", "content": get_content(int(sys.argv[3]))},
      ]
    },
  )
  print(res.json())
