import pytest
from app.core.config import Settings


def test_config_loads_from_env():
    settings = Settings(_env_file=None)
    assert settings.app_name == "Manan AI Test"
    assert settings.env == "test"
    assert settings.embedding_dimension == 384
    assert settings.database_url == "postgresql://postgres:postgres@localhost:5432/manan_ai_test"


def test_missing_required_env_var_raises_error(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(Exception) as exc_info:
        Settings(_env_file=None)
    err_text = str(exc_info.value).lower()
    assert "database_url" in err_text or "validation error" in err_text


def test_no_chroma_or_local_upload_dir_settings_present():
    settings = Settings(_env_file=None)
    assert not hasattr(settings, "chroma_dir")
    assert not hasattr(settings, "chroma_collection")
    assert not hasattr(settings, "documents_dir")
    assert not hasattr(settings, "upload_dir")
    # Verify Ollama Cloud settings are present
    assert hasattr(settings, "ollama_api_key")
    assert hasattr(settings, "ollama_base_url")
    assert hasattr(settings, "ollama_model")


def test_docker_database_url_formats(monkeypatch):
    # Docker internal URL (backend container -> postgres service)
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/manan_ai")
    settings_docker = Settings(_env_file=None)
    assert "postgres:5432" in settings_docker.database_url

    # Host machine URL (developer tool -> exposed port 5433)
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/manan_ai")
    settings_host = Settings(_env_file=None)
    assert "localhost:5433" in settings_host.database_url


# ----------------------------------------------------------------------
# Provider Validation Tests (Gemini & Ollama Cloud)
# ----------------------------------------------------------------------

def test_gemini_provider_succeeds(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")

    settings = Settings(_env_file=None)
    assert settings.llm_provider == "gemini"
    assert settings.google_api_key == "test-google-key"


def test_gemini_missing_api_key_fails(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GOOGLE_API_KEY", "")

    with pytest.raises(Exception) as exc_info:
        Settings(_env_file=None)
    err_msg = str(exc_info.value)
    assert "GOOGLE_API_KEY" in err_msg


def test_ollama_provider_succeeds(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_API_KEY", "test-cloud-api-key")
    monkeypatch.setenv("OLLAMA_BASE_URL", "https://ollama.com")
    monkeypatch.setenv("OLLAMA_MODEL", "gpt-oss:120b")

    settings = Settings(_env_file=None)
    assert settings.llm_provider == "ollama"
    assert settings.ollama_api_key == "test-cloud-api-key"
    assert settings.ollama_base_url == "https://ollama.com"
    assert settings.ollama_model == "gpt-oss:120b"


def test_ollama_missing_api_key_fails(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_API_KEY", "")
    monkeypatch.setenv("OLLAMA_BASE_URL", "https://ollama.com")

    with pytest.raises(Exception) as exc_info:
        Settings(_env_file=None)
    err_msg = str(exc_info.value)
    assert "OLLAMA_API_KEY" in err_msg


def test_ollama_missing_base_url_fails(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_API_KEY", "test-cloud-api-key")
    monkeypatch.setenv("OLLAMA_BASE_URL", "")

    with pytest.raises(Exception) as exc_info:
        Settings(_env_file=None)
    err_msg = str(exc_info.value)
    assert "OLLAMA_BASE_URL" in err_msg


def test_unsupported_provider_fails(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "unsupported_provider")

    with pytest.raises(Exception) as exc_info:
        Settings(_env_file=None)
    err_msg = str(exc_info.value)
    assert "Unsupported LLM provider" in err_msg
    assert "unsupported_provider" in err_msg


def test_hf_ocr_config(monkeypatch):
    monkeypatch.setenv("HF_API_TOKEN", "hf_secret_123")
    monkeypatch.setenv("HF_OCR_MODEL", "Qwen/Qwen2.5-VL-72B-Instruct")

    settings = Settings(_env_file=None)
    assert settings.hf_api_token == "hf_secret_123"
    assert settings.hf_ocr_model == "Qwen/Qwen2.5-VL-72B-Instruct"

