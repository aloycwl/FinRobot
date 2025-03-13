import sys
from models import cmodel
from prompt import content

headers = {"Authorization": "Bearer 3pGy7evw1rR761jeFezGC0hbdViHyE7VmuERBXYW", "Content-Type": "application/json"}

url = f"https://api.cloudflare.com/client/v4/accounts/8ac195cfff3622ab9b19e3c95a3d9c44/ai/run/{cmodel[int(sys.argv[1])]}"

print(requests.post(url, headers=headers, json={"messages":[{"role":"system","content":"you are top financial trader"}, {"role":"user","content":content[int(sys.argv[2])]}]}).json())