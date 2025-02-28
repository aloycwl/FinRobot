from google import genai
from PIL import Image

client = genai.Client(api_key="AIzaSyDNRRmbNTQER4HzL367i7dVF-mVDDr8YdA")
mo = 'gemini-2.0-flash-lite'

### Test connection using API
# response = client.models.generate_content(
#     model = mo, contents="Explain how AI works"
# )

### Test generation AI
response = client.models.generate_content(
    model = mo, contents='Tell me a story in 300 words.'
)

### Test image recognition
# response = client.models.generate_content(
#     model = mo, contents=['Tell a story based on this image', Image.open('1.jpg')]
# )

print(response.text)

### Test streaming
# for chunk in client.models.generate_content_stream(
#   model = mo, contents = 'Tell a random story in 100 words.'
# ): print(chunk.text)

### Enable below to see prompt summary
# print(response.model_dump_json(exclude_none=True, indent=4))