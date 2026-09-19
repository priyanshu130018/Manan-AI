import pytest
from unittest.mock import patch, MagicMock
from app.integrations.llm.factory import LLMFactory
from app.core.exceptions import LLMError, DocumentProcessingError
from app.main import create_app
from fastapi.testclient import TestClient


def test_get_llm_routing_factory_gemini():
    with patch("langchain_google_genai.ChatGoogleGenerativeAI") as mock_gemini:
        mock_gemini.return_value = MagicMock()
        model = LLMFactory.get_chat_model(provider="gemini", model_name="gemini-3.6-flash")
        assert model is not None


def test_get_llm_routing_factory_qwen():
    with patch("app.integrations.qwen.client.ChatQwen") as mock_qwen:
        mock_qwen.return_value = MagicMock()
        model = LLMFactory.get_chat_model(provider="qwen", model_name="qwen3.8-27b")
        assert model is not None


def test_get_llm_auto_route_qwen_by_model_name():
    with patch("app.integrations.qwen.client.ChatQwen") as mock_qwen:
        mock_qwen.return_value = MagicMock()
        model = LLMFactory.get_chat_model(provider=None, model_name="qwen3.8-27b")
        assert model is not None


def test_get_llm_mismatched_provider_model_raises_llm_error():
    with pytest.raises(LLMError) as exc_info:
        LLMFactory.get_chat_model(provider="gemini", model_name="qwen3.8-27b")
    assert "Qwen model" in str(exc_info.value)
    assert exc_info.value.provider == "gemini"
    assert exc_info.value.model == "qwen3.8-27b"

    with pytest.raises(LLMError) as exc_info2:
        LLMFactory.get_chat_model(provider="qwen", model_name="gemini-3.6-flash")
    assert "Gemini model" in str(exc_info2.value)
    assert exc_info2.value.provider == "qwen"
    assert exc_info2.value.model == "gemini-3.6-flash"


@pytest.mark.parametrize("obsolete_model", [
    "llama3.2:3b",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-3-pro",
    "llama3.2:latest",
    "philatest",
    "deepseek-coder:latest",
    "qwen2.5-coder:latest",
    "phi3:latest",
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
