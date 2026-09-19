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


def test_no_chroma_or_ollama_settings_present():
    settings = Settings(_env_file=None)
    assert not hasattr(settings, "chroma_dir")
    assert not hasattr(settings, "chroma_collection")
    assert not hasattr(settings, "ollama_base_url")
    assert not hasattr(settings, "ollama_model")


# ----------------------------------------------------------------------
# Provider Validation Tests (Gemini & Qwen)
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


def test_qwen_with_all_variables_succeeds(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "qwen")
    monkeypatch.setenv("QWEN_API_KEY", "test-qwen-key")
    monkeypatch.setenv("QWEN_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
    monkeypatch.setenv("QWEN_MODEL", "qwen3.8-27b")

    settings = Settings(_env_file=None)
    assert settings.llm_provider == "qwen"
    assert settings.qwen_api_key == "test-qwen-key"
    assert settings.qwen_base_url == "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    assert settings.qwen_model == "qwen3.8-27b"


def test_qwen_missing_api_key_fails(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "qwen")
    monkeypatch.setenv("QWEN_API_KEY", "")
    monkeypatch.setenv("QWEN_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
    monkeypatch.setenv("QWEN_MODEL", "qwen3.8-27b")

    with pytest.raises(Exception) as exc_info:
        Settings(_env_file=None)
    err_msg = str(exc_info.value)
    assert "QWEN_API_KEY" in err_msg


def test_qwen_missing_base_url_fails(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "qwen")
    monkeypatch.setenv("QWEN_API_KEY", "test-qwen-key")
    monkeypatch.setenv("QWEN_BASE_URL", "")
    monkeypatch.setenv("QWEN_MODEL", "qwen3.8-27b")

    with pytest.raises(Exception) as exc_info:
        Settings(_env_file=None)
    err_msg = str(exc_info.value)
    assert "QWEN_BASE_URL" in err_msg


def test_unsupported_provider_fails(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")

    with pytest.raises(Exception) as exc_info:
        Settings(_env_file=None)
    err_msg = str(exc_info.value)
    assert "Unsupported LLM provider" in err_msg
    assert "ollama" in err_msg
