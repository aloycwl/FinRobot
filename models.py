import config as cf
import os
from dotenv import load_dotenv

load_dotenv()


def md(cm, co) -> str:
  ro = [{"role": "system", "content": cm}, {"role": "user", "content": co}]

  if cf.ml == "nvidia":
    from openai import OpenAI
    return OpenAI(base_url="https://integrate.api.nvidia.com/v1",
                  api_key=os.getenv("NV")).chat.completions.create(
                      model=cf.mo,
                      messages=ro,
                      temperature=0.2,
                      top_p=0.7,
                      max_tokens=8192,
                      extra_body={
                          "chat_template_kwargs": {
                              "thinking": False
                          }
                      },
                      stream=False).choices[0].message.content

  if cf.ml == "gemini":
    from google import genai as ga
    from google.genai import types
    return ga.Client(api_key=os.getenv("GK")).models.generate_content(
        model=cf.mo,
        contents=co,
        config=types.GenerateContentConfig(temperature=0.1)).text

  elif cf.ml == "groq":
    from groq import Groq as gr
    return gr(api_key=os.getenv("QK")).chat.completions.create(
        model=cf.mo, messages=ro).choices[0].message.content

  elif cf.ml == "ollama":
    import ollama as ol
    return ol.chat(model=cf.mo, messages=ro)["message"]["content"]

  else:
    import requests as rq
    return rq.post(
        f"https://api.cloudflare.com/client/v4/accounts/{os.getenv('CA')}/ai/run/{cf.mo}",
        headers={
            "Authorization": f"Bearer {os.getenv('CK')}",
            "Content-Type": "application/json",
        },
        json={
            "messages": ro
        }).json()
