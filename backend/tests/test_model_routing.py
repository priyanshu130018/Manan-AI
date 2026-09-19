import pytest
from unittest.mock import patch, MagicMock
from langchain_ollama import ChatOllama
from app.integrations.llm.factory import LLMFactory
from app.core.exceptions import LLMError, DocumentProcessingError
from app.main import create_app
from fastapi.testclient import TestClient


def test_get_llm_routing_factory_gemini():
    with patch("langchain_google_genai.ChatGoogleGenerativeAI") as mock_gemini:
        mock_gemini.return_value = MagicMock()
        model = LLMFactory.get_chat_model(provider="gemini", model_name="gemini-3.6-flash")
        assert model is not None


def test_get_llm_routing_factory_ollama():
    model = LLMFactory.get_chat_model(provider="ollama", model_name="gpt-oss:120b")
    assert isinstance(model, ChatOllama)
    assert model.model == "gpt-oss:120b"
    assert "https://ollama.com" in model.base_url


def test_get_llm_auto_route_ollama_by_model_name():
    model = LLMFactory.get_chat_model(provider=None, model_name="gpt-oss:120b")
    assert isinstance(model, ChatOllama)
    assert model.model == "gpt-oss:120b"


def test_get_llm_mismatched_provider_model_raises_llm_error():
    with pytest.raises(LLMError) as exc_info:
        LLMFactory.get_chat_model(provider="gemini", model_name="gpt-oss:120b")
    assert "Ollama Cloud" in str(exc_info.value) or "gemini" in str(exc_info.value).lower()
    assert exc_info.value.provider == "gemini"
    assert exc_info.value.model == "gpt-oss:120b"

    with pytest.raises(LLMError) as exc_info2:
        LLMFactory.get_chat_model(provider="ollama", model_name="gemini-3.6-flash")
    assert "Gemini model" in str(exc_info2.value)
    assert exc_info2.value.provider == "ollama"
    assert exc_info2.value.model == "gemini-3.6-flash"


@pytest.mark.parametrize("obsolete_model", [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-3-pro",
    "philatest",
    "deepseek-coder:latest",
    "phi3:latest",
    "qwen3.8-27b",
    "qwen3-coder:480b",
    "qwen3-coder:480b-cloud",
    "unknown-model-xyz",
])
def test_get_llm_unsupported_model_raises_llm_error(obsolete_model):
    with pytest.raises(LLMError) as exc_info:
        LLMFactory.get_chat_model(model_name=obsolete_model)
    assert "Unsupported model" in str(exc_info.value)
    assert exc_info.value.model == obsolete_model


def test_llm_error_constructor_kwargs():
    err = LLMError("Test message", provider="gemini", model="gemini-3.6-flash")
    assert err.message == "Test message"
    assert err.provider == "gemini"
    assert err.model == "gemini-3.6-flash"
    assert err.error_code == "LLMError"


def test_manan_exception_handler_does_not_raise_attribute_error():
    app = create_app()

    @app.get("/test-doc-error")
    def raise_doc_error():
        raise DocumentProcessingError("Failed to extract text from PDF.")

    client = TestClient(app)
    res = client.get("/test-doc-error")
    assert res.status_code in [400, 422, 500]
    data = res.json()
    assert data["success"] is False
    assert data["message"] == "Failed to extract text from PDF."
    assert "error_code" in data
    assert data["error_code"] == "DocumentProcessingError"
