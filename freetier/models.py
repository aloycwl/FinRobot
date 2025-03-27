import os
import sys as sy

def md(cm, co) -> str:
  ro = [{"role":"system","content":cm},{"role":"user","content":co}]
  se = sy.argv[1]

  if se == "gemini":
    from google import genai as ga
    from google.genai import types
    from modelGemini import mo
    print(ga.Client(api_key=os.getenv("GK")).models.generate_content(
      model=mo(),
      contents=co,
      config=types.GenerateContentConfig(temperature=0.1)
    ).text)

  elif se == "groq":
    from modelGroq import mo
    from groq import Groq as gr
    print(gr(api_key=os.getenv("QK")).chat.completions.create(model=mo(),messages=ro).choices[0].message.content)

  elif se == "ollama":
    import ollama as ol
    from modelOllama import mo
    print(ol.chat(model=mo(),messages=ro)["message"]["content"])

  else:
    import requests as rq
    from modelCloudflare import mo
    print(rq.post(
      f"https://api.cloudflare.com/client/v4/accounts/{os.getenv('CA')}/ai/run/{mo()}",
      headers={"Authorization": f"Bearer {os.getenv('CK')}",
      "Content-Type": "application/json",
      },json={"messages": ro}).json())