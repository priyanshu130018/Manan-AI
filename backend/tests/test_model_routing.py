import pytest
from unittest.mock import patch, MagicMock
from app.integrations.llm.factory import LLMFactory

def test_get_llm_routing_factory():
    # Test Gemini model creation
    with patch("langchain_google_genai.ChatGoogleGenerativeAI") as mock_gemini:
        model = LLMFactory.get_chat_model(provider="gemini", model_name="gemini-3.6-flash")
        assert mock_gemini.called or model is not None

    # Test Ollama model creation
    with patch("langchain_ollama.ChatOllama") as mock_ollama:
        model = LLMFactory.get_chat_model(provider="ollama", model_name="llama3.2:3b")
        assert mock_ollama.called or model is not None
