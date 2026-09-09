from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(alias="APP_NAME")
    env: str = Field(alias="ENV")
    host: str = Field(alias="HOST")
    port: int = Field(alias="PORT")
    google_api_key: str = Field(alias="GOOGLE_API_KEY")
    gemini_model: str = Field(alias="GEMINI_MODEL")
    embedding_model: str = Field(alias="EMBEDDING_MODEL")
    chroma_db: str = Field(alias="CHROMA_DB")
    chroma_collection: str = Field(alias="CHROMA_COLLECTION")
    upload_dir: str = Field(alias="UPLOAD_DIR")

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()