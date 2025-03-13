import requests
import json
import sys

model = ['@cf/deepseek-ai/deepseek-r1-distill-qwen-32b', #0 | Text Generation
'@cf/deepseek-ai/deepseek-math-7b-instruct', #1
'@cf/defog/sqlcoder-7b-2', #2
'@cf/fblgit/una-cybertron-7b-v2-bf16', #3
'@cf/google/gemma-2b-it-lora', #4
'@cf/google/gemma-7b-it-lora', #5
'@cf/meta/llama-2-7b-chat-fp16', #6
'@cf/meta/llama-2-7b-chat-int8', #7
'@cf/meta/llama-3-8b-instruct', #8
'@cf/meta/llama-3-8b-instruct-awq', #9
'@cf/meta/llama-3.1-8b-instruct', #10
'@cf/meta/llama-3.1-8b-instruct-awq', #11
'@cf/meta/llama-3.1-8b-instruct-fp8', #12
'@cf/meta/llama-3.2-1b-instruct', #13
'@cf/meta/llama-3.2-3b-instruct', #14
'@cf/meta/llama-3.2-11b-vision-instruct', #15
'@cf/meta/llama-3.3-70b-instruct-fp8-fast', #16
'@cf/meta/llama-guard-3-8b', #17
'@cf/meta-llama/llama-2-7b-chat-hf-lora', #18
'@cf/microsoft/phi-2', #19
'@cf/mistral/mistral-7b-instruct-v0.1', #20
'@hf/mistral/mistral-7b-instruct-v0.2', #21
'@cf/mistral/mistral-7b-instruct-v0.2-lora', #22
'@cf/openchat/openchat-3.5-0106', #23
'@cf/qwen/qwen1.5-0.5b-chat', #24
'@cf/qwen/qwen1.5-1.8b-chat', #25
'@cf/qwen/qwen1.5-14b-chat-awq', #26
'@cf/qwen/qwen1.5-7b-chat-awq', #27
'@cf/tiiuae/falcon-7b-instruct', #28
'@cf/tinyllama/tinyllama-1.1b-chat-v1.0', #29
'@hf/google/gemma-7b-it', #30
'@hf/meta-llama/meta-llama-3-8b-instruct', #31
'@hf/mistral/mistral-7b-instruct-v0.2', #32
'@hf/nexusflow/starling-lm-7b-beta', #33
'@hf/nousresearch/hermes-2-pro-mistral-7b', #34
'@hf/thebloke/deepseek-coder-6.7b-base-awq', #35
'@hf/thebloke/deepseek-coder-6.7b-instruct-awq', #36
'@cf/thebloke/discolm-german-7b-v1-awq', #37
'@hf/thebloke/llama-2-13b-chat-awq', #38
'@hf/thebloke/llamaguard-7b-awq', #39
'@hf/thebloke/mistral-7b-instruct-v0.1-awq', #40
'@hf/thebloke/neural-chat-7b-v3-1-awq', #41
'@hf/thebloke/openhermes-2.5-mistral-7b-awq', #42
'@hf/thebloke/zephyr-7b-beta-awq', #43
'@cf/huggingface/distilbert-sst-2-int8', #44 | Text Classification
'@cf/openai/whisper', #45 | Automatic Speech Recognition
'@cf/openai/whisper-large-v3-turbo', #46
'@cf/openai/whisper-tiny-en', #47
'@cf/meta/m2m100-1.2b', #48 | Translation
'@cf/facebook/bart-large-cnn', #49 | Summarization
'@cf/baai/bge-base-en-v1.5', #50 | Text Embeddings
'@cf/baai/bge-small-en-v1.5', #51
'@cf/baai/bge-large-en-v1.5', #52
'@cf/black-forest-labs/flux-1-schnell', #53 | Text-to-image,
'@cf/bytedance/stable-diffusion-xl-lightning', #54
'@cf/lykon/dreamshaper-8-lcm', #55
'@cf/runwayml/stable-diffusion-v1-5-img2img', #56
'@cf/runwayml/stable-diffusion-v1-5-inpainting', #57
'@cf/stabilityai/stable-diffusion-xl-base-1.0', #58
'@cf/microsoft/resnet-50', #59 | Image Classification
'@cf/llava-hf/llava-1.5-7b-hf', #60 | Image-to-Text
'@cf/unum/uform-gen2-qwen-500m', #61
'@cf/facebook/detr-resnet-50'] #62 Object Detection

headers = {"Authorization": "Bearer 3pGy7evw1rR761jeFezGC0hbdViHyE7VmuERBXYW", "Content-Type": "application/json"}

url = f"https://api.cloudflare.com/client/v4/accounts/8ac195cfff3622ab9b19e3c95a3d9c44/ai/run/{model[int(sys.argv[1])]}"

content = ["share a short trading tip", #0
f"""Analyze the following forex price data. Give me a **price prediction** for the next trading day without any reasoning:
{json.dumps(requests.get("https://www.alphavantage.co/query?function=FX_DAILY&from_symbol=GBP&to_symbol=USD&interval=5min&apikey=8YUYO25GYPNE1EY8&outputsize=compact"
).json()["Time Series FX (Daily)"], indent=2)}""", #1
f"""Analyze the following cryptocurrency price data. Give me a **price prediction** for the next trading day without any reasoning:
{json.dumps(requests.get(f"https://www.alphavantage.co/query?function=DIGITAL_CURRENCY_DAILY&symbol=BTC&market=USD&apikey=8YUYO25GYPNE1EY8&outputsize=compact"
).json()["Time Series (Digital Currency Daily)"], indent=2)}""", #2
f"""Analyze the following stock price data. Give me a **price prediction** for the next trading day without any reasoning:
{json.dumps(requests.get(f"https://alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=NVDA&apikey=8YUYO25GYPNE1EY8&outputsize=compact"
).json()["Time Series (Daily)"], indent=2)}"""] #3

print(requests.post(url, headers=headers, json={"messages":[{"role":"system","content":"you are top financial trader"}, {"role":"user","content":content[int(sys.argv[2])]}]}).json())  