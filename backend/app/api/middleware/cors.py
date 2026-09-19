from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings


def setup_cors(app: FastAPI) -> None:
    settings = get_settings()
    configured = [origin.strip() for origin in settings.cors_allowed_origins.split(",") if origin.strip()]
    if settings.frontend_url and settings.frontend_url not in configured:
        configured.append(settings.frontend_url.strip())
    
    origins = list(set(configured))
    origins = [o for o in origins if o != "*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )