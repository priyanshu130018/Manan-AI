from app.models.entities.chunk import DocumentChunk
from app.services.retrieval_service import RetrievalService


def test_reciprocal_rank_fusion():
    retrieval_svc = RetrievalService(rrf_k=60)
    c1 = DocumentChunk(chunk_id="1", document_id="d1", filename="a.pdf", page_number=1, chunk_index=1, text="text 1")
    c2 = DocumentChunk(chunk_id="2", document_id="d1", filename="a.pdf", page_number=2, chunk_index=2, text="text 2")
    c3 = DocumentChunk(chunk_id="3", document_id="d2", filename="b.pdf", page_number=1, chunk_index=1, text="text 3")

    vector_candidates = [c1, c2]
    keyword_candidates = [c2, c3]

    reranked = retrieval_svc.reciprocal_rank_fusion(
        vector_candidates=vector_candidates,
        keyword_candidates=keyword_candidates,
        top_k=3,
    )
    assert len(reranked) == 3
    # c2 appeared in both vector and keyword candidates, so it should rank highest!
    assert reranked[0].chunk_id == "2"
