import ollama
import os
import requests
import sys
from models import *
from groq import Groq
from google import genai
from datasource import pmt

selection = sys.argv[1].lower()
content = pmt(sys.argv[3])
role = [{"role": "system", "content": "you are a top financial trader"},
  {"role": "user", "content": content}]

if selection == "gemini":
  client = genai.Client(api_key=os.getenv("GK"))
  text = client.models.generate_content(
    model=gmodel[int(sys.argv[2])],
    contents=content
  ).text

elif selection == "groq":
  client = Groq(api_key=os.getenv("QK"))
  text = client.chat.completions.create(
    model=qmodel[int(sys.argv[2])],
    messages=role
  ).choices[0].message.content

elif selection == "ollama":
  text = ollama.chat(
    model=int(sys.argv[2]), 
    messages=role)["message"]["content"]

else:
  headers = {
    "Authorization": f"Bearer {os.getenv('CK')}",
    "Content-Type": "application/json",
  }
  text = requests.post(
    f"https://api.cloudflare.com/client/v4/accounts/{os.getenv('CA')}/ai/run/{cmodel[int(sys.argv[2])]}",
    headers=headers,
    json={"messages": role}
  ).json()

print(text)