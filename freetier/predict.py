import ollama as ol
import os
import requests as re
import sys as sy
from datasource import pmt
from google import genai
from models import *
from groq import Groq

sel = sy.argv[1].lower()
con = pmt(sy.argv[3])
rol = [{"role":"system","content":"you are a top financial trader"},{"role":"user","content":con}]

if sel == "gemini":
  txt = genai.Client(api_key=os.getenv("GK")).models.generate_content(model=gm(),contents=con).text

elif sel == "groq":
  txt = Groq(api_key=os.getenv("QK")).chat.completions.create(model=qm(),messages=rol).choices[0].message.content

elif sel == "ollama":
  txt = ol.chat(model=om(),messages=rol)["message"]["content"]

else:
  txt = re.post(
    f"https://api.cloudflare.com/client/v4/accounts/{os.getenv('CA')}/ai/run/{cm()}",
    headers={
      "Authorization": f"Bearer {os.getenv('CK')}",
      "Content-Type": "application/json",
    },json={"messages": rol}).json()

print(txt)