import os
import requests
import sys
from models import cmodel
from prompt import content

headers = {
    "Authorization": f"Bearer {os.getenv('CK')}",
    "Content-Type": "application/json",
}

url = f"https://api.cloudflare.com/client/v4/accounts/{os.getenv('CA')}/ai/run/{cmodel[int(sys.argv[1])]}"

print(
    requests.post(
        url,
        headers=headers,
        json={
            "messages": [
                {"role": "system", "content": "you are top financial trader"},
                {"role": "user", "content": content[int(sys.argv[2])]},
            ]
        },
    ).json()
)
