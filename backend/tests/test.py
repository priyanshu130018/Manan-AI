from google import genai

from app.core.config import get_settings

settings = get_settings()

client = genai.Client(
    api_key=settings.google_api_key,
)

response = client.models.generate_content(
    model="gemini-3.6-flash",
    contents="Say hello in one sentence."
)

print(response.text)