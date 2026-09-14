from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.core.config import get_settings
from app.core.exceptions import (
    MananException,
    EntityNotFoundError,
    DocumentError,
    AIServiceError,
    LLMError,
    EmbeddingError,
    PersistenceError,
)
from app.core.logging import LoggerFactory
from app.models.database import get_database

logger = LoggerFactory.create_logger("Application")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("Starting Manan AI V2 (Authenticated LangChain Chatbot)...")
    logger.info("Listening on %s:%s", settings.host, settings.port)
    logger.info("Configured LLM Provider: %s, Model: %s", settings.llm_provider, settings.llm_model)

    try:
        db = get_database()
        logger.info("Database initialization check complete.")
    except Exception as e:
        logger.warning("Database startup check warning: %s", e)

    yield
    logger.info("Shutting down Manan AI V2...")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Manan AI API",
        description="Authenticated LangChain Chatbot with Multi-Model Support and Long-Term Memory.",
        version="1.0.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    origins = [origin.strip() for origin in settings.cors_allowed_origins.split(",") if origin.strip()]
    if not origins:
        origins = ["http://localhost:5174", "http://localhost:5173", "http://localhost:3000"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 1. Domain-specific exception handling
    @app.exception_handler(MananException)
    async def manan_exception_handler(request: Request, exc: MananException):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if isinstance(exc, EntityNotFoundError):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(exc, DocumentError):
            status_code = status.HTTP_400_BAD_REQUEST
        elif isinstance(exc, (AIServiceError, LLMError, EmbeddingError)):
            status_code = status.HTTP_502_BAD_GATEWAY
        elif isinstance(exc, PersistenceError):
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

        logger.warning("Domain exception caught [%s]: %s", exc.__class__.__name__, exc.message)
        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "message": exc.message,
                "error_code": exc.error_code,
                "details": exc.details if exc.details else None,
            },
        )

    # 2. FastAPI Request Validation Error handling
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning("Request validation error on %s: %s", request.url.path, exc.errors())
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "message": "Validation error in request data.",
                "error_code": "VALIDATION_ERROR",
                "details": exc.errors(),
            },
        )

    # 3. Standard FastAPI HTTPExceptions
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        detail_msg = exc.detail if isinstance(exc.detail, str) else "HTTP exception occurred."
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": detail_msg,
                "error_code": f"HTTP_{exc.status_code}",
            },
        )

    # 4. Global unhandled exceptions (No tracebacks or raw exception strings exposed)
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled internal server error on %s: %s", request.url.path, exc, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "An internal server error occurred. Please try again later.",
                "error_code": "INTERNAL_SERVER_ERROR",
            },
        )

    app.include_router(api_router)
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
