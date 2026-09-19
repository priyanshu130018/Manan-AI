import os
from functools import lru_cache
from pathlib import Path
from typing import Optional
from pydantic import Field, ValidationError as PydanticValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_project_root() -> Path:
    current = Path(__file__).resolve()
    # backend/app/core/config.py -> parents[3] is project root
    return current.parents[3]


PROJECT_ROOT = get_project_root()
ENV_FILE = str(PROJECT_ROOT / ".env")


class Settings(BaseSettings):
    # Core Application
    app_name: str = Field(alias="APP_NAME")
    env: str = Field(alias="ENV")
    host: str = Field(alias="HOST")
    port: int = Field(alias="PORT")

    # PostgreSQL Database (with pgvector)
    database_url: str = Field(alias="DATABASE_URL")

    # Authentication & Security
    jwt_secret_key: str = Field(alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(alias="REFRESH_TOKEN_EXPIRE_DAYS")
    session_expiry_days: int = Field(alias="SESSION_EXPIRY_DAYS")

    # Gemini & Google Integration
    google_api_key: str = Field(alias="GOOGLE_API_KEY")
    google_client_id: Optional[str] = Field(default=None, alias="GOOGLE_CLIENT_ID")
    google_client_secret: Optional[str] = Field(default=None, alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(alias="GOOGLE_REDIRECT_URI")
    frontend_url: str = Field(alias="FRONTEND_URL")

    # LLM Provider Configuration ("gemini" | "ollama")
    llm_provider: str = Field(alias="LLM_PROVIDER")
    llm_model: str = Field(alias="LLM_MODEL")

    # Ollama Cloud API Configuration
    ollama_api_key: Optional[str] = Field(default=None, alias="OLLAMA_API_KEY")
    ollama_base_url: str = Field(default="https://ollama.com", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="gpt-oss:120b", alias="OLLAMA_MODEL")

    # Cloudinary Document Storage
    cloudinary_cloud_name: Optional[str] = Field(default=None, alias="CLOUDINARY_CLOUD_NAME")
    cloudinary_api_key: Optional[str] = Field(default=None, alias="CLOUDINARY_API_KEY")
    cloudinary_api_secret: Optional[str] = Field(default=None, alias="CLOUDINARY_API_SECRET")
    cloudinary_folder: Optional[str] = Field(default="manan-ai", alias="CLOUDINARY_FOLDER")
    cloudinary_upload_preset: Optional[str] = Field(default=None, alias="CLOUDINARY_UPLOAD_PRESET")

    # Embeddings Configuration (PostgreSQL pgvector)
    embedding_provider: str = Field(alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(alias="EMBEDDING_MODEL")
    embedding_dimension: int = Field(alias="EMBEDDING_DIMENSION")

    # Document Processing Quotas & Limits
    max_upload_size_mb: int = Field(alias="MAX_UPLOAD_SIZE_MB")
    total_storage_limit_mb: int = Field(alias="TOTAL_STORAGE_LIMIT_MB")
    chunk_size: int = Field(alias="CHUNK_SIZE")
    chunk_overlap: int = Field(alias="CHUNK_OVERLAP")

    # Hugging Face Hosted Inference OCR Configuration
    hf_api_token: Optional[str] = Field(default=None, alias="HF_API_TOKEN")
    hf_ocr_model: str = Field(default="Qwen/Qwen2.5-VL-72B-Instruct", alias="HF_OCR_MODEL")

    # CORS
    cors_allowed_origins: str = Field(alias="CORS_ALLOWED_ORIGINS")

    @model_validator(mode="after")
    def validate_provider_and_credentials(self) -> "Settings":
        prov = (self.llm_provider or "").lower().strip()
        if prov not in {"gemini", "ollama"}:
            raise ValueError(
                f"Unsupported LLM provider '{self.llm_provider}'. Supported providers are: 'gemini', 'ollama'"
            )

        if prov == "ollama":
            if not self.ollama_api_key or not self.ollama_api_key.strip():
                raise ValueError(
                    "Missing required environment variable for Ollama Cloud provider: OLLAMA_API_KEY"
                )
            if not self.ollama_base_url or not self.ollama_base_url.strip():
                raise ValueError(
                    "Missing required environment variable for Ollama Cloud provider: OLLAMA_BASE_URL"
                )

        if prov == "gemini":
            if not self.google_api_key or not self.google_api_key.strip():
                raise ValueError(
                    "Missing required environment variable for Gemini provider: GOOGLE_API_KEY"
                )

        return self

    @property
    def gemini_model(self) -> str:
        return self.llm_model

    @property
    def database_path(self) -> str:
        return self.database_url

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def resolve_path(self, path_str: str) -> Path:
        p = Path(path_str)
        if p.is_absolute():
            return p
        return (PROJECT_ROOT / p).resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    try:
        settings = Settings()
    except PydanticValidationError as e:
        custom_messages = []
        missing_vars = []
        for err in e.errors():
            msg = err.get("msg", "")
            loc = err.get("loc", ())
            if "Value error, " in msg:
                custom_messages.append(msg.replace("Value error, ", ""))
            elif loc:
                missing_vars.append(str(loc[0]).upper())
            elif msg:
                custom_messages.append(msg)

        if custom_messages:
            error_detail = "; ".join(custom_messages)
        elif missing_vars:
            error_detail = f"Missing required environment variable(s): {', '.join(missing_vars)}"
        else:
            error_detail = str(e)

        raise RuntimeError(
            f"Configuration error: {error_detail}. Please check your .env file."
        ) from e

    return settings
