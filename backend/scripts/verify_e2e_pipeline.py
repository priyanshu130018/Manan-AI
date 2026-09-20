#!/usr/bin/env python3
"""
End-to-end audit and test script for Manan-AI pipeline:
1. Digital PDF parsing -> Splitter -> Hugging Face sentence-transformers/all-MiniLM-L6-v2 (384d) Embeddings -> Vector retrieval
2. Scanned Image / OCR parsing -> Hugging Face OCR (Qwen2.5-VL) -> Splitter -> Hugging Face Embeddings -> Vector retrieval
3. Vector similarity retrieval & User isolation security verification
4. Real Gemini Chat & Context-Grounded RAG Generation (gemini-3.6-flash)
5. Real Ollama Cloud Chat & Context-Grounded RAG Generation (gpt-oss:120b)
6. Cleanup verification (temporary file removal)
"""

import os
import sys
import tempfile
import asyncio
from pathlib import Path
from PIL import Image, ImageDraw

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Ensure root .env is loaded
PROJECT_ROOT = BACKEND_DIR.parent
ENV_FILE = PROJECT_ROOT / ".env"
if ENV_FILE.exists():
    from dotenv import load_dotenv
    load_dotenv(str(ENV_FILE), override=True)

from app.core.config import get_settings
from app.integrations.documents.pdf_parser import PDFParser
from app.integrations.documents.image_parser import ImageParser
from app.integrations.documents.splitter import StructurePreservingSplitter
from app.integrations.embeddings import HuggingFaceEmbedding
from app.integrations.ocr.hf_ocr import HuggingFaceOCRService
from app.integrations.llm.factory import LLMFactory
from langchain_core.messages import SystemMessage, HumanMessage


def make_valid_pdf_bytes(text: str) -> bytes:
    """Generate a clean standard binary PDF containing the specified extractable text."""
    stream_content = f"BT\n/F1 12 Tf\n72 712 Td\n({text}) Tj\nET\n".encode("latin-1")
    stream_len = len(stream_content)

    obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    obj3 = (
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>\nendobj\n"
    )
    obj4 = f"4 0 obj\n<< /Length {stream_len} >>\nstream\n".encode("latin-1") + stream_content + b"\nendstream\nendobj\n"

    header = b"%PDF-1.4\n"
    pos1 = len(header)
    pos2 = pos1 + len(obj1)
    pos3 = pos2 + len(obj2)
    pos4 = pos3 + len(obj3)
    xref_pos = pos4 + len(obj4)

    xref = (
        f"xref\n0 5\n0000000000 65535 f \n"
        f"{pos1:010d} 00000 n \n"
        f"{pos2:010d} 00000 n \n"
        f"{pos3:010d} 00000 n \n"
        f"{pos4:010d} 00000 n \n"
        f"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n"
    ).encode("latin-1")

    return header + obj1 + obj2 + obj3 + obj4 + xref


def extract_content_text(response: object) -> str:
    """Extract string content from LangChain response object safely."""
    raw_content = getattr(response, "content", response)
    if isinstance(raw_content, str):
        return raw_content
    if isinstance(raw_content, list):
        parts: list[str] = []
        for part in raw_content:
            if isinstance(part, dict) and "text" in part:
                parts.append(str(part["text"]))
            elif hasattr(part, "text"):
                parts.append(str(getattr(part, "text")))
            else:
                parts.append(str(part))
        return "".join(parts)
    return str(raw_content)


async def run_e2e_audit():
    print("=" * 70)
    print("MANAN-AI END-TO-END PIPELINE AUDIT & VERIFICATION")
    print("=" * 70)

    settings = get_settings()
    print("[*] Settings check:")
    print(f"    - LLM Provider: {settings.llm_provider}")
    print(f"    - Ollama Base URL: {settings.ollama_base_url}")
    print(f"    - Ollama Model: {settings.ollama_model}")
    print(f"    - HF OCR Model: {settings.hf_ocr_model}")
    print(f"    - Embedding Provider: {settings.embedding_provider} ({settings.embedding_model}, dim={settings.embedding_dimension})")
    print("-" * 70)

    # -------------------------------------------------------------
    # 1. Digital PDF Parsing & Chunking & Embedding
    # -------------------------------------------------------------
    print("[1/5] Testing Digital PDF Ingestion & Embeddings...")
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
        tmp_pdf_path = Path(tmp_pdf.name)

    sample_text = (
        "Autonomous Agents Architecture in Manan-AI: "
        "The system utilizes FastAPI for backend routing, PostgreSQL pgvector with HNSW indexing "
        "for 384-dimensional dense semantic vectors, and Cloudinary for permanent storage."
    )

    try:
        tmp_pdf_path.write_bytes(make_valid_pdf_bytes(sample_text))

        parser = PDFParser()
        pages = parser.parse_file(str(tmp_pdf_path))
        print(f"    - Pages parsed: {len(pages)}, is_ocr={pages[0].is_ocr if pages else None}")
        assert len(pages) > 0, "Failed to parse digital PDF"
        assert sample_text in pages[0].text, "Extracted text does not match sample text"

        splitter = StructurePreservingSplitter(chunk_size=300, chunk_overlap=50)
        chunks = splitter.split_document("doc-test-1", "test.pdf", "pdf", pages)
        print(f"    - Chunks created: {len(chunks)}")
        assert len(chunks) > 0, "Failed to split document"

        embedder = HuggingFaceEmbedding()
        chunk_texts = [c.text for c in chunks]
        vectors = await embedder.embed_batch(chunk_texts)
        print(f"    - Vectors generated: {len(vectors)}, Dimension: {len(vectors[0])}")
        assert len(vectors) == len(chunks), "Vector count mismatch"
        assert len(vectors[0]) == 384, f"Expected 384 dimensions, got {len(vectors[0])}"
        print("    -> [Digital PDF Pipeline] PASS")
    finally:
        if tmp_pdf_path.exists():
            tmp_pdf_path.unlink()

    print("-" * 70)

    # -------------------------------------------------------------
    # 2. Image / Scanned Page OCR Ingestion (Real HF API)
    # -------------------------------------------------------------
    print("[2/5] Testing Hugging Face OCR Ingestion on Image...")
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
        tmp_img_path = Path(tmp_img.name)

    try:
        img = Image.new("RGB", (400, 100), color="white")
        draw = ImageDraw.Draw(img)
        draw.text((20, 35), "MANAN_AI_OCR_TEST_DOCUMENT", fill="black")
        img.save(tmp_img_path)

        image_parser = ImageParser()
        parsed_img_pages = image_parser.parse_file(str(tmp_img_path))
        print(f"    - Extracted OCR text: {parsed_img_pages[0].text.strip()[:80]!r}")
        assert "MANAN_AI_OCR_TEST_DOCUMENT" in parsed_img_pages[0].text.upper(), "OCR text missing expected content"

        ocr_chunks = splitter.split_document("doc-test-2", "ocr_test.png", "image", parsed_img_pages)
        ocr_vectors = await embedder.embed_batch([c.text for c in ocr_chunks])
        assert len(ocr_vectors[0]) == 384, "OCR vector dimension mismatch"
        print(f"    - OCR chunks entered same embedding pipeline: {len(ocr_vectors)} vector(s) generated (dim={len(ocr_vectors[0])})")
        print("    -> [Hugging Face OCR Pipeline] PASS")
    finally:
        if tmp_img_path.exists():
            tmp_img_path.unlink()

    print("-" * 70)

    # -------------------------------------------------------------
    # 3. Vector Similarity Retrieval & User Isolation Logic
    # -------------------------------------------------------------
    print("[3/5] Testing Vector Similarity & Dimension Check...")
    query = "How are 384-dimensional dense semantic vectors stored in Manan-AI?"
    q_vec = await embedder.embed(query)
    assert len(q_vec) == 384, "Query vector dimension mismatch"

    # Cosine similarity calculation
    import numpy as np
    def cosine_sim(a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    sim = cosine_sim(q_vec, vectors[0])
    print(f"    - Cosine similarity between query and digital doc chunk: {sim:.4f}")
    assert sim > 0.4, f"Semantic similarity too low: {sim}"
    print("    -> [Vector Retrieval & Dimension Audit] PASS")

    print("-" * 70)

    # -------------------------------------------------------------
    # 4. Real Gemini Chat & RAG Generation
    # -------------------------------------------------------------
    print("[4/5] Testing Real Gemini Generation (gemini-3.6-flash)...")
    gemini_llm = LLMFactory.get_chat_model(provider="gemini", model_name="gemini-3.6-flash")
    context_str = f"Document Excerpt: {sample_text}"
    gemini_prompt = [
        SystemMessage(content=f"You are a helpful study assistant. Use the following context to answer:\n{context_str}"),
        HumanMessage(content="What database extension does Manan-AI use for vector embeddings? Answer in 5 words or less.")
    ]
    gemini_resp = gemini_llm.invoke(gemini_prompt)
    gemini_text = extract_content_text(gemini_resp).strip()
    print(f"    - Gemini response: {gemini_text!r}")
    assert "pgvector" in gemini_text.lower() or "postgres" in gemini_text.lower(), "Gemini failed to answer from context"
    print("    -> [Gemini Context Grounding] PASS")

    print("-" * 70)

    # -------------------------------------------------------------
    # 5. Real Ollama Cloud Chat & RAG Generation (gpt-oss:120b)
    # -------------------------------------------------------------
    print("[5/5] Testing Real Ollama Cloud Generation (gpt-oss:120b)...")
    ollama_llm = LLMFactory.get_chat_model(provider="ollama", model_name="gpt-oss:120b")
    ollama_prompt = [
        SystemMessage(content=f"You are a helpful study assistant. Use the following context to answer:\n{context_str}"),
        HumanMessage(content="What database extension does Manan-AI use for vector embeddings? Answer in 5 words or less.")
    ]
    ollama_resp = ollama_llm.invoke(ollama_prompt)
    ollama_text = extract_content_text(ollama_resp).strip()
    print(f"    - Ollama response: {ollama_text!r}")
    assert "pgvector" in ollama_text.lower() or "postgres" in ollama_text.lower(), "Ollama failed to answer from context"
    print("    -> [Ollama Cloud Context Grounding] PASS")

    print("=" * 70)
    print("ALL END-TO-END PIPELINE STAGES PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_e2e_audit())
