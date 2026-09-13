from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import api_router
from app.core.config import get_settings
from app.core.logging import LoggerFactory

logger = LoggerFactory.create_logger("Application")

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("Starting Manan AI V1 (Anonymous Gemini Chatbot)...")
    logger.info("Listening on %s:%s", settings.host, settings.port)
    logger.info("Configured Gemini LLM: %s", settings.gemini_model)
    logger.info("Configured Embedding Model: %s", settings.embedding_model)
    yield
    logger.info("Shutting down Manan AI V1...")

def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Manan AI V1 API",
        description="Simple Anonymous Gemini Chatbot with optional Document RAG.",
        version="1.0.0",
        docs_url="/v1/docs",
        openapi_url="/v1/openapi.json",
        lifespan=lifespan,
    )

    origins = [origin.strip() for origin in settings.cors_allowed_origins.split(",") if origin.strip()]
    if not origins:
        origins = ["http://localhost:5173", "http://localhost:3000"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Prefix all routes with /v1
    app.include_router(api_router, prefix="/v1")
    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
