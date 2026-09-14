import os
from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

def get_version_root() -> Path:
    current = Path(__file__).resolve()
    # v2/backend/app/core/config.py -> parents[3] is v2
    return current.parents[3]


VERSION_ROOT = get_version_root()
ENV_FILE = str(VERSION_ROOT / ".env")


class Settings(BaseSettings):
    app_name: str = Field(default="Manan AI", alias="APP_NAME")
    env: str = Field(default="development", alias="ENV")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    database_url: str = Field(
        default="postgresql://postgres:sql0000@localhost:5432/manan_ai",
        alias="DATABASE_URL",
    )
    jwt_secret_key: str = Field(
        default="manan-ai-super-secret-jwt-key-for-local-dev-change-in-prod",
        alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=1440, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")
    session_expiry_days: int = Field(default=7, alias="SESSION_EXPIRY_DAYS")

    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    google_client_id: str | None = Field(default=None, alias="GOOGLE_CLIENT_ID")
    google_client_secret: str | None = Field(default=None, alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(
        default="http://localhost:8000/auth/google/callback",
        alias="GOOGLE_REDIRECT_URI",
    )
    frontend_url: str = Field(
        default="http://localhost:8080/v2",
        alias="FRONTEND_URL",
    )

    llm_provider: str = Field(default="gemini", alias="LLM_PROVIDER")
    llm_model: str = Field(default="gemini-3.6-flash", alias="LLM_MODEL")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3.2:3b", alias="OLLAMA_MODEL")

    embedding_provider: str = Field(default="local", alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(default="gemini-embedding-001", alias="EMBEDDING_MODEL")

    data_dir: str = Field(default="./data", alias="DATA_DIR")
    chroma_dir: str = Field(default="./data/chroma", alias="CHROMA_PERSIST_DIRECTORY")
    documents_dir: str = Field(default="./data/documents", alias="UPLOAD_DIR")
    chroma_collection: str = Field(default="documents", alias="CHROMA_COLLECTION")

    max_upload_size_mb: int = Field(default=50, alias="MAX_UPLOAD_SIZE_MB")
    total_storage_limit_mb: int = Field(default=500, alias="TOTAL_STORAGE_LIMIT_MB")
    chunk_size: int = Field(default=1000, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, alias="CHUNK_OVERLAP")
    tesseract_cmd: str | None = Field(default=None, alias="TESSERACT_CMD")

    cors_allowed_origins: str = Field(
        default="http://localhost:5174,http://localhost:5173,http://localhost:3000",
        alias="CORS_ALLOWED_ORIGINS",
    )

    @property
    def gemini_model(self) -> str:
        return self.llm_model

    @property
    def database_path(self) -> str:
        return self.database_url

    @property
    def chroma_db(self) -> str:
        return self.chroma_dir

    @property
    def upload_dir(self) -> str:
        return self.documents_dir

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
        return (VERSION_ROOT / p).resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    docs_path = settings.resolve_path(settings.documents_dir)
    docs_path.mkdir(parents=True, exist_ok=True)
    settings.documents_dir = str(docs_path)

    chroma_path = settings.resolve_path(settings.chroma_dir)
    chroma_path.mkdir(parents=True, exist_ok=True)
    settings.chroma_dir = str(chroma_path)

    data_path = settings.resolve_path(settings.data_dir)
    data_path.mkdir(parents=True, exist_ok=True)
    settings.data_dir = str(data_path)

    return settings
