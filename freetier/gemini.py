import requests
import sys
from google import genai
from models import gmodel
from prompt import content

print(
    genai.Client(api_key="AIzaSyDNRRmbNTQER4HzL367i7dVF-mVDDr8YdA")
    .models.generate_content(
        model=gmodel[int(sys.argv[1])], contents=content[int(sys.argv[2])]
    )
    .text
)
