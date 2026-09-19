import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_ollama import ChatOllama

from app.integrations.llm.factory import LLMFactory
from app.integrations.storage.cloudinary_storage import CloudinaryStorage
from app.core.exceptions import LLMError, DocumentProcessingError


def test_chat_ollama_initialization_with_headers():
    llm = LLMFactory.get_chat_model(
        provider="ollama",
        model_name="gpt-oss:120b",
    )
    assert isinstance(llm, ChatOllama)
    assert llm.model == "gpt-oss:120b"
    assert "https://ollama.com" in llm.base_url
    assert "headers" in llm.client_kwargs
    assert "Authorization" in llm.client_kwargs["headers"]


def test_cloudinary_storage_upload_and_delete():
    with patch("cloudinary.uploader.upload") as mock_upload, patch(
        "cloudinary.uploader.destroy"
    ) as mock_destroy:
        mock_upload.return_value = {
            "public_id": "manan-ai/users/user1/documents/doc1",
            "secure_url": "https://res.cloudinary.com/demo/image/upload/v1/manan-ai/users/user1/documents/doc1.pdf",
            "resource_type": "raw",
        }
        mock_destroy.return_value = {"result": "ok"}

        storage = CloudinaryStorage(
            cloud_name="demo",
            api_key="123",
            api_secret="sec",
            folder="manan-ai",
            upload_preset="manan-preset",
        )

        upload_res = storage.upload_file(
            file_obj=b"dummy content",
            filename="test.pdf",
            user_id="user1",
            document_id="doc1",
        )
        assert upload_res["cloudinary_public_id"] == "manan-ai/users/user1/documents/doc1"
        assert upload_res["cloudinary_secure_url"].startswith("https://")

        storage.delete_file("manan-ai/users/user1/documents/doc1", resource_type="raw")
        mock_destroy.assert_called_once_with(
            "manan-ai/users/user1/documents/doc1", resource_type="raw", invalidate=True
        )


def test_cloudinary_unconfigured_raises_error_no_fake_success():
    storage = CloudinaryStorage(
        cloud_name="",
        api_key="",
        api_secret="",
    )
    assert not storage.is_configured
    with pytest.raises(DocumentProcessingError) as exc_info:
        storage.upload_file(
            file_obj=b"data",
            filename="test.pdf",
            user_id="user1",
            document_id="doc1",
        )
    assert "Cloudinary credentials are not configured" in str(exc_info.value)


def test_cloudinary_upload_failure_raises_document_processing_error():
    with patch("cloudinary.uploader.upload", side_effect=Exception("Network timeout")):
        storage = CloudinaryStorage(
            cloud_name="demo",
            api_key="123",
            api_secret="sec",
        )
        with pytest.raises(DocumentProcessingError) as exc_info:
            storage.upload_file(
                file_obj=b"data",
                filename="test.pdf",
                user_id="user1",
                document_id="doc1",
            )
        assert "Failed to upload document to Cloudinary storage" in str(exc_info.value)


def test_models_endpoint_returns_gemini_and_ollama(client):
    res = client.get("/llm/models")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "gemini" in data["data"]
    assert "ollama" in data["data"]
    assert "qwen" not in data["data"]
    assert "gpt-oss:120b" in data["data"]["ollama"]["models"][0]["value"]
