import os
import sys as sy

def models(cm, co):
  ro = [{"role":"system","content":cm},{"role":"user","content":co}]
  mo = int(sy.argv[2])
  se = sy.argv[1].lower()

  if se == "gemini":
    from google import genai as ga
    from google.genai import types
    from modelGemini import mg
    return ga.Client(api_key=os.getenv("GK")).models.generate_content(
      model=mg[mo],
      contents=co,
      config=types.GenerateContentConfig(temperature=0.1)
    ).text

  elif se == "groq":
    from modelGroq import mq
    from groq import Groq as gr
    return gr(api_key=os.getenv("QK")).chat.completions.create(model=mq[mo],messages=ro).choices[0].message.content

  elif se == "ollama":
    import ollama as ol
    from modelOllama import ml
    return ol.chat(model=ml[mo],messages=ro)["message"]["content"]

  else:
    import requests as rq
    from modelCloudflare import mc
    return(rq.post(
      f"https://api.cloudflare.com/client/v4/accounts/{os.getenv('CA')}/ai/run/{mc[mo]}",
      headers={"Authorization": f"Bearer {os.getenv('CK')}",
      "Content-Type": "application/json",
      },json={"messages": ro}).json())