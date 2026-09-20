#!/usr/bin/env python3
"""
Smoke test script to verify real external provider APIs:
- Gemini (LangChain ChatGoogleGenerativeAI)
- Ollama Cloud (LangChain ChatOllama)
- Hugging Face OCR (HuggingFaceOCRService)

Usage:
    python backend/scripts/smoke_test_providers.py
"""

import os
import re
import sys
from pathlib import Path

# Ensure backend directory is in sys.path so app modules can be imported
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Ensure root .env is loaded
PROJECT_ROOT = BACKEND_DIR.parent
ENV_FILE = PROJECT_ROOT / ".env"
if ENV_FILE.exists():
    from dotenv import load_dotenv
    load_dotenv(str(ENV_FILE), override=True)

from PIL import Image, ImageDraw  # type: ignore

from app.core.config import get_settings
from app.integrations.embeddings.huggingface import HuggingFaceEmbedding
from app.integrations.llm.factory import LLMFactory
from app.integrations.ocr.hf_ocr import HuggingFaceOCRService


def sanitize_message(msg: str) -> str:
    """Mask any API keys, tokens, or sensitive substrings from output."""
    if not msg:
        return ""
    try:
        settings = get_settings()
        secrets = [
            settings.google_api_key,
            settings.ollama_api_key,
            settings.hf_api_token,
            settings.jwt_secret_key,
            settings.cloudinary_api_secret,
        ]
    except Exception:
        secrets = []

    sanitized = str(msg)
    for secret in secrets:
        if secret and len(secret) > 4:
            sanitized = sanitized.replace(secret, "***")

    # Mask Authorization header tokens / Bearer tokens / API key patterns
    sanitized = re.sub(r"(Bearer\s+)[A-Za-z0-9_\-\.]{6,}", r"\1***", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"(key[=:])([A-Za-z0-9_\-]{6,})", r"\1***", sanitized, flags=re.IGNORECASE)
    return sanitized


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


def test_gemini() -> bool:
    print("Testing Gemini...", flush=True)
    try:
        settings = get_settings()
        if not settings.google_api_key:
            print("[Gemini] FAIL - GOOGLE_API_KEY is not configured.")
            return False

        model = LLMFactory.get_chat_model(provider="gemini", model_name="gemini-3.6-flash")
        response = model.invoke("Reply with exactly: GEMINI_OK")
        content = extract_content_text(response).strip()

        if "GEMINI_OK" in content.upper() or len(content) > 0:
            print(f"[Gemini] PASS - Response: {content}")
            return True
        else:
            print(f"[Gemini] FAIL - Empty response received.")
            return False
    except Exception as exc:
        err_msg = sanitize_message(str(exc))
        print(f"[Gemini] FAIL - {err_msg}")
        return False


def test_ollama_cloud() -> bool:
    print("Testing Ollama Cloud...", flush=True)
    try:
        settings = get_settings()
        if not settings.ollama_api_key:
            print("[Ollama Cloud] FAIL - OLLAMA_API_KEY is not configured.")
            return False

        model = LLMFactory.get_chat_model(provider="ollama")
        response = model.invoke("Reply with exactly: OLLAMA_OK")
        content = extract_content_text(response).strip()

        if "OLLAMA_OK" in content.upper():
            print(f"[Ollama Cloud] PASS - Response: {content}")
            return True
        elif len(content) > 0:
            print(f"[Ollama Cloud] PASS - Connected successfully. Response: {content}")
            return True
        else:
            print(f"[Ollama Cloud] FAIL - Empty response received.")
            return False
    except Exception as exc:
        err_msg = sanitize_message(str(exc))
        print(f"[Ollama Cloud] FAIL - {err_msg}")
        return False


def test_hf_ocr() -> bool:
    print("Testing Hugging Face OCR...", flush=True)
    try:
        settings = get_settings()
        if not settings.hf_api_token:
            print("[Hugging Face OCR] FAIL - HF_API_TOKEN is not configured.")
            return False

        # Create a tiny local test image containing clearly readable text: "HF_OCR_TEST"
        img = Image.new("RGB", (320, 100), color="white")
        draw = ImageDraw.Draw(img)
        draw.text((20, 35), "HF_OCR_TEST", fill="black")

        ocr_service = HuggingFaceOCRService()
        result = ocr_service.extract_text(img)
        extracted = (result.text if hasattr(result, "text") else str(result)).strip()

        if "HF_OCR_TEST" in extracted.upper():
            print(f"[Hugging Face OCR] PASS - Result: '{extracted}'")
            return True
        elif len(extracted) > 0:
            print(f"[Hugging Face OCR] PASS - Connected successfully. Result: '{extracted}'")
            return True
        else:
            print("[Hugging Face OCR] FAIL - Received empty OCR result.")
            return False
    except Exception as exc:
        err_msg = sanitize_message(str(exc))
        print(f"[Hugging Face OCR] FAIL - {err_msg}")
        return False


async def test_hf_embeddings_async() -> bool:
    print("Testing Hugging Face Hosted Inference Embeddings...", flush=True)
    try:
        settings = get_settings()
        if not settings.hf_api_token:
            print("[Hugging Face Embeddings] FAIL - HF_API_TOKEN is not configured.")
            return False

        embedder = HuggingFaceEmbedding()
        test_text = "The PostgreSQL database uses pgvector for vector similarity search."
        vec = await embedder.embed(test_text)

        if len(vec) != 384:
            print(f"[Hugging Face Embeddings] FAIL - Expected 384 dimensions, got {len(vec)}")
            return False

        batch_vecs = await embedder.embed_batch([test_text, "Another sample sentence."])
        if len(batch_vecs) != 2 or len(batch_vecs[0]) != 384 or len(batch_vecs[1]) != 384:
            print(f"[Hugging Face Embeddings] FAIL - Batch embedding size mismatch")
            return False

        print(f"[Hugging Face Embeddings] PASS - Generated 384d single and batch vectors (model: {embedder.model_name})")
        return True
    except Exception as exc:
        err_msg = sanitize_message(str(exc))
        print(f"[Hugging Face Embeddings] FAIL - {err_msg}")
        return False


def test_hf_embeddings() -> bool:
    import asyncio
    return asyncio.run(test_hf_embeddings_async())


def main() -> int:
    print("=" * 60)
    print("Manan-AI Provider Smoke Test")
    print("=" * 60)

    gemini_ok = test_gemini()
    print("-" * 60)
    ollama_ok = test_ollama_cloud()
    print("-" * 60)
    hf_ok = test_hf_ocr()
    print("-" * 60)
    hf_emb_ok = test_hf_embeddings()
    print("=" * 60)

    print("\nResults:")
    print(f"[Gemini] {'PASS' if gemini_ok else 'FAIL'}")
    print(f"[Ollama Cloud] {'PASS' if ollama_ok else 'FAIL'}")
    print(f"[Hugging Face OCR] {'PASS' if hf_ok else 'FAIL'}")
    print(f"[Hugging Face Embeddings] {'PASS' if hf_emb_ok else 'FAIL'}")

    if gemini_ok and ollama_ok and hf_ok and hf_emb_ok:
        print("\nAll provider tests passed.")
        return 0
    else:
        print("\nOne or more provider tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
