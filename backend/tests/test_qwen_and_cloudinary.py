import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from app.integrations.qwen.client import QwenClient, ChatQwen
from app.integrations.storage.cloudinary_storage import CloudinaryStorage
from app.core.exceptions import LLMError, AuthenticationError


@pytest.mark.asyncio
async def test_qwen_client_generate_text():
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Hello from Qwen model!",
                }
            }
        ]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        client = QwenClient(
            api_key="test-key",
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            model="qwen3.8-27b",
        )
        result = await client.generate_text("Say hello")
        assert result == "Hello from Qwen model!"
        await client.aclose()


@pytest.mark.asyncio
async def test_qwen_client_error_handling():
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 401
    mock_response.text = "Invalid API Key"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        client = QwenClient(
            api_key="bad-key",
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            model="qwen3.8-27b",
        )
        with pytest.raises(AuthenticationError) as exc_info:
            await client.generate_text("test")
        assert "invalid qwen api key" in str(exc_info.value).lower()
        await client.aclose()


@pytest.mark.asyncio
async def test_chat_qwen_ainvoke():
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Answer from ChatQwen",
                }
            }
        ]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        chat = ChatQwen(
            api_key="test-key",
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            model_name="qwen3.8-27b",
        )
        messages = [
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content="Hello!"),
        ]
        response = await chat.ainvoke(messages)
        assert isinstance(response, AIMessage)
        assert response.content == "Answer from ChatQwen"


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


def test_models_endpoint_returns_gemini_and_qwen(client):
    res = client.get("/llm/models")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "gemini" in data["data"]
    assert "qwen" in data["data"]
    assert "ollama" not in data["data"]
