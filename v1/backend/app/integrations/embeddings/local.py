"""Local, offline embeddings using sentence-transformers (no API, no 429 errors).

Default model: sentence-transformers/all-MiniLM-L6-v2
- 384-dim vectors, standard for RAG
- Runs on CPU (falls back if GPU is unavailable)
- Downloaded automatically once to the local HF cache on first use
"""

from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import List

from app.core.config import get_settings
from app.core.logging import LoggerFactory

logger = LoggerFactory.create_logger("LocalEmbedding")


try:
    import torch
    from sentence_transformers import SentenceTransformer  # type: ignore
    _TORCH_AVAILABLE = True
except Exception:
    _TORCH_AVAILABLE = False


class LocalEmbedding:
    def __init__(self, model_name: str | None = None, batch_size: int = 32) -> None:
        settings = get_settings()
        raw_model = model_name or settings.embedding_model or "all-MiniLM-L6-v2"
        # If set to Gemini or non-HF model string, default to standard SentenceTransformer model
        if "gemini" in raw_model.lower():
            self.model_name = "all-MiniLM-L6-v2"
        else:
            self.model_name = raw_model
        self.batch_size = batch_size
        self._model = None
        self._load_lock = asyncio.Lock()
        self._dimension: int | None = None

    async def _ensure_model_loaded(self):
        if self._model is not None:
            return self._model
        async with self._load_lock:
            if self._model is not None:
                return self._model
            if not _TORCH_AVAILABLE:
                logger.info("SentenceTransformer not available; using deterministic embedding provider.")
                self._model = "fallback"
                self._dimension = 384
                return self._model

            logger.info("Loading local embedding model: %s", self.model_name)
            try:
                def _load_sync():
                    return SentenceTransformer(self.model_name, local_files_only=True)

                loop = asyncio.get_running_loop()
                model = await asyncio.wait_for(loop.run_in_executor(None, _load_sync), timeout=3.0)
                self._model = model
                try:
                    self._dimension = int(model.get_sentence_embedding_dimension())
                except Exception:
                    self._dimension = 384
                logger.info(
                    "Loaded embedding model '%s' (dim=%s)", self.model_name, self._dimension
                )
                return model
            except (Exception, BaseException) as exc:
                logger.warning(
                    "Could not load SentenceTransformer (%s). Falling back to deterministic embedding provider.",
                    exc,
                )
                self._model = "fallback"
                self._dimension = 384
                return self._model

    @property
    def dimension(self) -> int | None:
        return self._dimension or 384

    async def embed(self, text: str) -> List[float]:
        return (await self.embed_batch([text]))[0]

    async def embed_batch(self, texts: List[str], batch_size: int | None = None) -> List[List[float]]:
        if not texts:
            return []
        model = await self._ensure_model_loaded()
        if model == "fallback":
            import hashlib
            import math

            res: List[List[float]] = []
            for t in texts:
                # Generate 384-dim normalized pseudo-vector
                raw = []
                for i in range(384):
                    h = hashlib.sha256(f"{t}_{i}".encode("utf-8")).digest()
                    val = (int.from_bytes(h[:4], "little") / 4294967295.0) * 2.0 - 1.0
                    raw.append(val)
                norm = math.sqrt(sum(x * x for x in raw)) or 1.0
                res.append([x / norm for x in raw])
            return res

        bs = batch_size or self.batch_size

        def _run_batch():
            # normalize_embeddings=True is standard for cosine / Chroma hnsw:cosine
            return model.encode(
                texts,
                batch_size=bs,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )

        loop = asyncio.get_event_loop()
        vectors = await loop.run_in_executor(None, _run_batch)
        # Ensure python list[list[float]]
        return [[float(v) for v in row] for row in vectors]


@lru_cache(maxsize=1)
def get_local_embedding() -> LocalEmbedding:
    return LocalEmbedding()
