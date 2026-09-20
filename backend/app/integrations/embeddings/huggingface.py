"""Hugging Face hosted inference embeddings client.

Uses Hugging Face Hosted Inference API over HTTPS for remote embedding generation
without loading or executing model weights locally inside the container.
Default model: sentence-transformers/all-MiniLM-L6-v2 (384-dimensional vectors).
"""

from __future__ import annotations

import asyncio
import math
from functools import lru_cache
from typing import List, Optional

import httpx

from app.core.config import get_settings
from app.core.exceptions import EmbeddingError
from app.core.logging import LoggerFactory

logger = LoggerFactory.create_logger("HuggingFaceEmbedding")


class HuggingFaceEmbedding:
    """
    Client for generating embeddings using the Hugging Face Hosted Inference API.
    Zero local PyTorch or model weight dependencies.
    """

    def __init__(
        self,
        api_token: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: float = 60.0,
        batch_size: int = 32,
    ) -> None:
        settings = get_settings()
        self.api_token = (api_token or settings.hf_api_token or "").strip()
        raw_model = model_name or settings.embedding_model or "sentence-transformers/all-MiniLM-L6-v2"
        # Normalize model identifier
        if raw_model == "all-MiniLM-L6-v2":
            self.model_name = "sentence-transformers/all-MiniLM-L6-v2"
        else:
            self.model_name = raw_model

        self.timeout = timeout
        self.batch_size = batch_size
        self._dimension = settings.embedding_dimension or 384

        logger.info(
            "Initialized HuggingFaceEmbedding (model=%s, dim=%d, remote=True)",
            self.model_name,
            self._dimension,
        )

    @property
    def dimension(self) -> int:
        return self._dimension

    def _get_headers(self) -> dict[str, str]:
        if not self.api_token:
            raise EmbeddingError(
                "Hugging Face API token (HF_API_TOKEN) is not configured. "
                "Please set HF_API_TOKEN in your environment variables."
            )
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    def _get_endpoint(self) -> str:
        return f"https://router.huggingface.co/hf-inference/models/{self.model_name}/pipeline/feature-extraction"

    def _validate_vector(self, vec: list[float], index_desc: str = "result") -> list[float]:
        if not isinstance(vec, list):
            raise EmbeddingError(
                f"Invalid embedding shape: expected list of floats for {index_desc}, got {type(vec).__name__}"
            )
        if len(vec) != self._dimension:
            raise EmbeddingError(
                f"Embedding dimension mismatch for {index_desc}: expected {self._dimension}, got {len(vec)}"
            )
        for i, val in enumerate(vec):
            if not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
                raise EmbeddingError(
                    f"Invalid embedding element at index {i} in {index_desc}: {val}"
                )
        return [float(v) for v in vec]

    async def _request_with_retry(
        self,
        payload: dict,
        max_retries: int = 3,
    ) -> httpx.Response:
        url = self._get_endpoint()
        headers = self._get_headers()

        attempt = 0
        while True:
            attempt += 1
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, headers=headers, json=payload)

                if response.status_code == 200:
                    return response

                # Rate limiting (429) or Model Loading (503)
                if response.status_code in (429, 503) and attempt <= max_retries:
                    backoff = 2.0 ** attempt
                    if response.status_code == 503:
                        try:
                            body = response.json()
                            if "estimated_time" in body:
                                backoff = min(float(body["estimated_time"]), 15.0)
                        except Exception:
                            pass
                    logger.warning(
                        "Hugging Face Inference API returned HTTP %d on attempt %d/%d. Retrying in %.1fs...",
                        response.status_code,
                        attempt,
                        max_retries,
                        backoff,
                    )
                    await asyncio.sleep(backoff)
                    continue

                # Handle specific HTTP error codes with safe error messages (no token leakage)
                if response.status_code == 401:
                    raise EmbeddingError(
                        "Hugging Face API authentication failed (HTTP 401). Verify that HF_API_TOKEN is valid."
                    )
                elif response.status_code == 404:
                    raise EmbeddingError(
                        f"Model '{self.model_name}' was not found on Hugging Face Hosted Inference API (HTTP 404)."
                    )
                elif response.status_code == 429:
                    raise EmbeddingError(
                        "Hugging Face Inference API rate limit reached (HTTP 429). Please wait before retrying."
                    )
                elif response.status_code == 503:
                    raise EmbeddingError(
                        f"Hugging Face model '{self.model_name}' is currently loading (HTTP 503). "
                        "Please try again shortly."
                    )
                else:
                    raise EmbeddingError(
                        f"Hugging Face embedding request failed (HTTP {response.status_code}): {response.text[:200]}"
                    )

            except httpx.RequestError as exc:
                if attempt <= max_retries:
                    backoff = 2.0 ** attempt
                    logger.warning(
                        "Network error connecting to Hugging Face API on attempt %d/%d (%s). Retrying in %.1fs...",
                        attempt,
                        max_retries,
                        str(exc),
                        backoff,
                    )
                    await asyncio.sleep(backoff)
                    continue
                logger.error("Hugging Face embedding network error after %d attempts: %s", max_retries, exc)
                raise EmbeddingError(f"Network error connecting to Hugging Face embedding API: {exc}") from exc

    async def embed(self, text: str) -> List[float]:
        """
        Generate a single 384-dimensional vector embedding for the input text.
        """
        if not text or not text.strip():
            # Return zero vector for empty text or raise error
            raise EmbeddingError("Cannot generate embedding for empty text.")

        payload = {"inputs": text}
        response = await self._request_with_retry(payload)

        try:
            data = response.json()
        except Exception as exc:
            raise EmbeddingError(f"Malformed JSON response from Hugging Face: {exc}") from exc

        # HF feature extraction endpoint returns [float, ...] for single string inputs
        if isinstance(data, list):
            # If returned as [[float, ...]] (nested 1-item batch)
            if len(data) > 0 and isinstance(data[0], list):
                return self._validate_vector(data[0], index_desc="single text embedding")
            return self._validate_vector(data, index_desc="single text embedding")

        raise EmbeddingError(
            f"Unexpected response format from Hugging Face embedding API: expected list, got {type(data).__name__}"
        )

    async def embed_batch(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
    ) -> List[List[float]]:
        """
        Generate 384-dimensional vector embeddings for a list of input texts.
        Batches requests to prevent payload size and timeout issues.
        """
        if not texts:
            return []

        bs = batch_size or self.batch_size
        results: List[List[float]] = []

        for i in range(0, len(texts), bs):
            chunk = texts[i : i + bs]
            # Clean and ensure non-empty strings
            cleaned_chunk = [t if (t and t.strip()) else " " for t in chunk]

            payload = {"inputs": cleaned_chunk}
            response = await self._request_with_retry(payload)

            try:
                data = response.json()
            except Exception as exc:
                raise EmbeddingError(f"Malformed JSON batch response from Hugging Face: {exc}") from exc

            if not isinstance(data, list):
                raise EmbeddingError(
                    f"Unexpected batch response format from Hugging Face API: expected list, got {type(data).__name__}"
                )

            if len(data) != len(chunk):
                raise EmbeddingError(
                    f"Batch response size mismatch: expected {len(chunk)} embeddings, got {len(data)}"
                )

            for idx, item in enumerate(data):
                validated = self._validate_vector(item, index_desc=f"batch item {i + idx}")
                results.append(validated)

        return results


@lru_cache(maxsize=1)
def get_huggingface_embedding() -> HuggingFaceEmbedding:
    return HuggingFaceEmbedding()
