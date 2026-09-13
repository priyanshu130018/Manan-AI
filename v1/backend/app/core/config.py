import os
from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

def get_backend_root() -> Path:
    current = Path(__file__).resolve()
    # backend/app/core/config.py -> parents[2] is v1/backend
    return current.parents[2]

BACKEND_ROOT = get_backend_root()
ENV_FILE = str(BACKEND_ROOT / ".env")

class Settings(BaseSettings):
    app_name: str = Field(default="Manan V1", alias="APP_NAME")
    env: str = Field(default="development", alias="ENV")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8001, alias="PORT")

    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    gemini_model: str = Field(default="gemini-3.6-flash", alias="GEMINI_MODEL")
    embedding_model: str = Field(default="gemini-embedding-001", alias="EMBEDDING_MODEL")
    embedding_provider: str = Field(default="local", alias="EMBEDDING_PROVIDER")

    data_dir: str = Field(default="./data", alias="DATA_DIR")
    database_url: str = Field(
        default="postgresql://postgres:sql0000@localhost:5432/manan_ai_v1",
        alias="DATABASE_URL",
    )
    chroma_dir: str = Field(default="./data/chroma_v1", alias="CHROMA_PERSIST_DIRECTORY")
    documents_dir: str = Field(default="./data/uploads_v1", alias="UPLOAD_DIR")
    chroma_collection: str = Field(default="documents_v1", alias="CHROMA_COLLECTION")

    max_upload_size_mb: int = Field(default=50, alias="MAX_UPLOAD_SIZE_MB")
    total_storage_limit_mb: int = Field(default=500, alias="TOTAL_STORAGE_LIMIT_MB")
    chunk_size: int = Field(default=1000, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, alias="CHUNK_OVERLAP")
    tesseract_cmd: str | None = Field(default=None, alias="TESSERACT_CMD")
    cors_allowed_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        alias="CORS_ALLOWED_ORIGINS",
    )

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

    def validate_api_key(self) -> None:
        key = self.google_api_key.strip()
        if not key or key == "your_gemini_api_key_here":
            raise ValueError("GOOGLE_API_KEY is not configured in v1/backend/.env.")

    def resolve_path(self, path_str: str) -> Path:
        p = Path(path_str)
        if p.is_absolute():
            return p
        return (BACKEND_ROOT / p).resolve()


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
