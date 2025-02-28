from google import genai

client = genai.Client(api_key="AIzaSyDNRRmbNTQER4HzL367i7dVF-mVDDr8YdA")

# Test connection using API
# response = client.models.generate_content(
#     model="gemini-2.0-flash", contents="Explain how AI works"
# )

# Test generation AI
response = client.models.generate_content(
    model='gemini-2.0-flash',
    contents='Tell me a story in 300 words.'
)


print(response.text)

# Enable below to see prompt summary
# print(response.model_dump_json(exclude_none=True, indent=4))