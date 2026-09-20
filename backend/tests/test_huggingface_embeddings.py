import math
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest

from app.core.config import Settings
from app.core.exceptions import EmbeddingError
from app.integrations.embeddings import HuggingFaceEmbedding, get_huggingface_embedding
from app.services.document_service import DocumentService
from app.services.retrieval_service import RetrievalService


@pytest.mark.asyncio
async def test_hf_embedding_success_single():
    embedder = HuggingFaceEmbedding(api_token="hf_test_token_123", model_name="sentence-transformers/all-MiniLM-L6-v2")
    assert embedder.dimension == 384

    mock_vec = [0.05 * (i % 10) for i in range(384)]
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_vec

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp) as mock_post:
        result = await embedder.embed("The PostgreSQL database uses pgvector.")
        assert len(result) == 384
        assert result == mock_vec
        mock_post.assert_called_once()
        headers = mock_post.call_args.kwargs.get("headers", {})
        assert headers.get("Authorization") == "Bearer hf_test_token_123"
        assert headers.get("Content-Type") == "application/json"
        assert mock_post.call_args.kwargs.get("json") == {"inputs": "The PostgreSQL database uses pgvector."}


@pytest.mark.asyncio
async def test_hf_embedding_success_batch():
    embedder = HuggingFaceEmbedding(api_token="hf_test_token_123", model_name="sentence-transformers/all-MiniLM-L6-v2")
    texts = ["First test text.", "Second test text."]
    mock_vec1 = [0.1] * 384
    mock_vec2 = [0.2] * 384

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = [mock_vec1, mock_vec2]

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp) as mock_post:
        results = await embedder.embed_batch(texts)
        assert len(results) == 2
        assert len(results[0]) == 384
        assert len(results[1]) == 384
        assert results[0] == mock_vec1
        assert results[1] == mock_vec2


@pytest.mark.asyncio
async def test_hf_embedding_empty_text_raises_error():
    embedder = HuggingFaceEmbedding(api_token="hf_test_token_123")
    with pytest.raises(EmbeddingError) as exc_info:
        await embedder.embed("")
    assert "empty text" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_hf_embedding_empty_batch_returns_empty_list():
    embedder = HuggingFaceEmbedding(api_token="hf_test_token_123")
    results = await embedder.embed_batch([])
    assert results == []


@pytest.mark.asyncio
async def test_hf_embedding_dimension_mismatch_raises_error():
    embedder = HuggingFaceEmbedding(api_token="hf_test_token_123")
    # Response has 768 dimensions instead of 384
    invalid_vec = [0.1] * 768
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = invalid_vec

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        with pytest.raises(EmbeddingError) as exc_info:
            await embedder.embed("Test text")
        assert "dimension mismatch" in str(exc_info.value).lower()
        assert "expected 384" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_hf_embedding_nan_value_raises_error():
    embedder = HuggingFaceEmbedding(api_token="hf_test_token_123")
    invalid_vec = [0.1] * 383 + [float("nan")]
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = invalid_vec

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        with pytest.raises(EmbeddingError) as exc_info:
            await embedder.embed("Test text")
        assert "invalid embedding element" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_hf_embedding_missing_token_raises_error():
    embedder = HuggingFaceEmbedding(api_token="")
    with pytest.raises(EmbeddingError) as exc_info:
        await embedder.embed("Test text")
    assert "HF_API_TOKEN" in str(exc_info.value)


@pytest.mark.asyncio
async def test_hf_embedding_http_error_handling():
    embedder = HuggingFaceEmbedding(api_token="hf_test_token_123")

    for status_code, snippet in [
        (401, "authentication failed"),
        (404, "not found"),
        (429, "rate limit"),
    ]:
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = status_code
        mock_resp.text = f"Error {status_code}"

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            with pytest.raises(EmbeddingError) as exc_info:
                await embedder.embed("Test text")
            assert snippet.lower() in str(exc_info.value).lower()


def test_health_endpoint_reports_huggingface_provider(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["embedding_provider"] == "huggingface"
    assert data["embedding_model"] == "sentence-transformers/all-MiniLM-L6-v2"
    assert data["embedding_dimension"] == 384


from app.core.config import Settings, get_settings


def test_document_service_unsupported_provider_raises_error(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "unsupported_provider")
    get_settings.cache_clear()
    try:
        with pytest.raises(EmbeddingError) as exc_info:
            DocumentService()
        assert "Unsupported embedding provider" in str(exc_info.value)
    finally:
        get_settings.cache_clear()


def test_retrieval_service_unsupported_provider_raises_error(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "unsupported_provider")
    get_settings.cache_clear()
    try:
        with pytest.raises(EmbeddingError) as exc_info:
            RetrievalService()
        assert "Unsupported embedding provider" in str(exc_info.value)
    finally:
        get_settings.cache_clear()
