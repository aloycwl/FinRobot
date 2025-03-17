cmodel = [
    # Text Generation
    '@cf/deepseek-ai/deepseek-r1-distill-qwen-32b',  # 0
    '@cf/deepseek-ai/deepseek-math-7b-instruct',     # 1
    '@cf/defog/sqlcoder-7b-2',                       # 2
    '@cf/fblgit/una-cybertron-7b-v2-bf16',           # 3
    '@cf/google/gemma-2b-it-lora',                   # 4
    '@cf/google/gemma-7b-it-lora',                   # 5
    '@cf/meta/llama-2-7b-chat-fp16',                 # 6
    '@cf/meta/llama-2-7b-chat-int8',                 # 7
    '@cf/meta/llama-3-8b-instruct',                  # 8
    '@cf/meta/llama-3-8b-instruct-awq',              # 9
    '@cf/meta/llama-3.1-8b-instruct',                # 10
    '@cf/meta/llama-3.1-8b-instruct-awq',            # 11
    '@cf/meta/llama-3.1-8b-instruct-fp8',            # 12
    '@cf/meta/llama-3.2-1b-instruct',                # 13
    '@cf/meta/llama-3.2-3b-instruct',                # 14
    '@cf/meta/llama-3.2-11b-vision-instruct',        # 15
    '@cf/meta/llama-3.3-70b-instruct-fp8-fast',      # 16
    '@cf/meta/llama-guard-3-8b',                     # 17
    '@cf/meta-llama/llama-2-7b-chat-hf-lora',        # 18
    '@cf/microsoft/phi-2',                           # 19
    '@cf/mistral/mistral-7b-instruct-v0.1',          # 20
    '@hf/mistral/mistral-7b-instruct-v0.2',          # 21
    '@cf/mistral/mistral-7b-instruct-v0.2-lora',     # 22
    '@cf/openchat/openchat-3.5-0106',                # 23
    '@cf/qwen/qwen1.5-0.5b-chat',                    # 24
    '@cf/qwen/qwen1.5-1.8b-chat',                    # 25
    '@cf/qwen/qwen1.5-14b-chat-awq',                 # 26
    '@cf/qwen/qwen1.5-7b-chat-awq',                  # 27
    '@cf/tiiuae/falcon-7b-instruct',                 # 28
    '@cf/tinyllama/tinyllama-1.1b-chat-v1.0',        # 29
    # Text Classification
    '@cf/huggingface/distilbert-sst-2-int8',         # 44
    # Automatic Speech Recognition
    '@cf/openai/whisper',                            # 45
    '@cf/openai/whisper-large-v3-turbo',             # 46
    '@cf/openai/whisper-tiny-en',                    # 47
    # Translation
    '@cf/meta/m2m100-1.2b',                          # 48
    # Summarization
    '@cf/facebook/bart-large-cnn',                   # 49
    # Text Embeddings
    '@cf/baai/bge-base-en-v1.5',                     # 50
    '@cf/baai/bge-small-en-v1.5',                    # 51
    '@cf/baai/bge-large-en-v1.5',                    # 52
    # Text-to-image
    '@cf/black-forest-labs/flux-1-schnell',          # 53
    '@cf/bytedance/stable-diffusion-xl-lightning',   # 54
    '@cf/lykon/dreamshaper-8-lcm',                   # 55
    '@cf/runwayml/stable-diffusion-v1-5-img2img',    # 56
    '@cf/runwayml/stable-diffusion-v1-5-inpainting', # 57
    '@cf/stabilityai/stable-diffusion-xl-base-1.0',  # 58
    # Image Classification
    '@cf/microsoft/resnet-50',                       # 59
    # Image-to-Text
    '@cf/llava-hf/llava-1.5-7b-hf',                  # 60
    '@cf/unum/uform-gen2-qwen-500m',                 # 61
    # Object Detection
    '@cf/facebook/detr-resnet-50'                    # 62
]

gmodel = [
    'gemini-2.0-flash-lite',            # 0
    'gemini-2.0-flash',                 # 1
    'gemini-1.5-flash',                 # 2
    'gemini-1.5-flash-8b',              # 3
    'gemini-1.5-pro',                   # 4
    'text-embedding-004'                # 5
]

omodel = [
    'qwen2:0.5b'                        # 0
]

qmodel = [
    'deepseek-r1-distill-llama-70b',    # 0
    'deepseek-r1-distill-qwen-32b',     # 1
    'allam-2-7b',                       # 2
    'gemma2-9b-it',                     # 3
    'llama-3.1-8b-instant',             # 4
    'llama-3.2-11b-vision-preview',     # 5
    'llama-3.2-1b-preview',             # 6
    'llama-3.2-3b-preview',             # 7
    'llama-3.2-90b-vision-preview',     # 8
    'llama-3.3-70b-specdec',            # 9
    'llama-3.3-70b-versatile',          # 10
    'llama-guard-3-8b',                 # 11
    'llama3-70b-8192',                  # 12
    'llama3-8b-8192',                   # 13
    'mistral-saba-24b',                 # 14
    'mixtral-8x7b-32768',               # 15
    'qwen-2.5-32b',                     # 16
    'qwen-2.5-coder-32b',               # 17
    'qwen-qwq-32b',                     # 18
    # Object Detection
    'distil-whisper-large-v3-en',       # 19
    'whisper-large-v3',                 # 20
    'whisper-large-v3-turbo'            # 21
]