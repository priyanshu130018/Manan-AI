import pytest
from unittest.mock import AsyncMock, MagicMock
from app.models.entities.chunk import DocumentChunk
from app.repositories.vector_repository import VectorRepository
from app.services.retrieval_service import RetrievalService


@pytest.mark.asyncio
async def test_vector_repository_vector_formatting():
    vec = [0.1, 0.25, -0.3]
    formatted = VectorRepository._format_vector(vec)
    assert formatted.startswith("[")
    assert formatted.endswith("]")
    assert "0.100000" in formatted
    assert "0.250000" in formatted


@pytest.mark.asyncio
async def test_retrieval_service_pgvector_integration():
    mock_vector_repo = MagicMock()
    from app.models.schemas.retrieval import RetrievedChunk
    
    mock_vector_repo.search = AsyncMock()
    
    async def fake_search(embedding, top_k=5, document_ids=None, user_id=None):
        return [
            RetrievedChunk(
                id="c-1",
                document="Photosynthesis converts light into chemical energy.",
                metadata={"document_id": "doc-1", "filename": "biology.pdf", "page": 1, "chunk": 0},
                distance=0.05,
                score=0.95,
            )
        ]
    
    mock_vector_repo.search.side_effect = fake_search

    mock_doc_repo = MagicMock()
    mock_doc_repo.list_all.return_value = []
    
    mock_embedding = MagicMock()
    mock_embedding.embed = AsyncMock(return_value=[0.1] * 384)

    service = RetrievalService(
        vector_repo=mock_vector_repo,
        doc_repo=mock_doc_repo,
        embedding=mock_embedding,
    )

    results = await service.retrieve_vectors(query="What is photosynthesis?")
    assert len(results) == 1
    assert results[0].chunk_id == "c-1"
    assert "Photosynthesis" in results[0].text
    assert results[0].score == 0.95


@pytest.mark.asyncio
async def test_vector_repository_dimension_mismatch_raises_error():
    mock_db = MagicMock()
    repo = VectorRepository(db=mock_db)

    # 1. Invalid dimension (e.g. 768 or 3 instead of 384) must raise ValueError
    invalid_embedding = [0.1] * 768
    with pytest.raises(ValueError) as exc_info:
        await repo.add(
            ids=["chunk-1"],
            documents=["Sample text"],
            embeddings=[invalid_embedding],
            metadatas=[{"document_id": "doc-1"}],
        )
    assert "Embedding dimension mismatch" in str(exc_info.value)
    assert "expected 384, got 768" in str(exc_info.value)

    # 2. Valid dimension (384) accepted without raising
    valid_embedding = [0.1] * 384
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_db.get_connection.return_value.__enter__.return_value = mock_conn

    await repo.add(
        ids=["chunk-valid"],
        documents=["Valid text"],
        embeddings=[valid_embedding],
        metadatas=[{"document_id": "doc-1"}],
    )
    assert mock_cursor.execute.called
