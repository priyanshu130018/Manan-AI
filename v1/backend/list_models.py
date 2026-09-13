import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google import genai
from app.core.config import get_settings


settings = get_settings()

client = genai.Client(
    api_key=settings.google_api_key,
)

for model in client.models.list():
    print("=" * 80)
    print(model.name)
    print(getattr(model, "display_name", None))
    print(getattr(model, "supported_actions", None))