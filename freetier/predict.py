import ollama
import os
import requests
import sys
from models import *
from groq import Groq
from google import genai
from datasource import pmt

sel = sys.argv[1].lower()
con = pmt(sys.argv[3])
rol = [{"role": "system", "content": "you are a top financial trader"},
  {"role": "user", "content": con}]

if sel == "gemini":
  txt = genai.Client(api_key=os.getenv("GK")).models.generate_content(model=gm(),contents=con).text

elif sel == "groq":
  txt = Groq(api_key=os.getenv("QK")).chat.completions.create(model=qm(),messages=rol).choices[0].message.content

elif sel == "ollama":
  txt = ollama.chat(model=om(),messages=rol)["message"]["content"]

else:
  txt = requests.post(
    f"https://api.cloudflare.com/client/v4/accounts/{os.getenv('CA')}/ai/run/{cm()}",
    headers={
      "Authorization": f"Bearer {os.getenv('CK')}",
      "Content-Type": "application/json",
    },json={"messages": rol}).json()

print(txt)