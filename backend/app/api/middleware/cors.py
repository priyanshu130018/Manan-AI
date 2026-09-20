from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings


def setup_cors(app: FastAPI) -> None:
    settings = get_settings()
    configured = [origin.strip().rstrip("/") for origin in settings.cors_allowed_origins.split(",") if origin.strip()]
    if settings.frontend_url:
        fe_origin = settings.frontend_url.strip().rstrip("/")
        if fe_origin and fe_origin not in configured:
            configured.append(fe_origin)
    
    origins = list(set(configured))
    origins = [o for o in origins if o != "*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )