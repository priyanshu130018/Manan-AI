"""Local embeddings using sentence-transformers.

Default model: sentence-transformers/all-MiniLM-L6-v2
- 384-dim vectors, standard for RAG
- Runs on CPU/GPU
"""

from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import List

from app.core.config import get_settings
from app.core.exceptions import EmbeddingError
from app.core.logging import LoggerFactory

logger = LoggerFactory.create_logger("LocalEmbedding")


try:
    from sentence_transformers import SentenceTransformer  # type: ignore
    _SENTENCE_TRANSFORMERS_AVAILABLE = True
except Exception:
    _SENTENCE_TRANSFORMERS_AVAILABLE = False


class LocalEmbedding:
    def __init__(self, model_name: str | None = None, batch_size: int = 32) -> None:
        settings = get_settings()
        raw_model = model_name or settings.embedding_model or "all-MiniLM-L6-v2"
        if "gemini" in raw_model.lower():
            self.model_name = "all-MiniLM-L6-v2"
        else:
            self.model_name = raw_model
        self.batch_size = batch_size
        self._model = None
        self._load_lock = asyncio.Lock()
        self._dimension: int | None = 384

    async def _ensure_model_loaded(self):
        if self._model is not None:
            return self._model
        async with self._load_lock:
            if self._model is not None:
                return self._model
            if not _SENTENCE_TRANSFORMERS_AVAILABLE:
                raise EmbeddingError(
                    "sentence-transformers is not installed. Please install sentence-transformers to use local embeddings."
                )

            logger.info("Loading local embedding model: %s", self.model_name)
            try:
                def _load_sync():
                    return SentenceTransformer(self.model_name)

                loop = asyncio.get_running_loop()
                model = await loop.run_in_executor(None, _load_sync)
                self._model = model
                try:
                    self._dimension = int(model.get_sentence_embedding_dimension())
                except Exception:
                    self._dimension = 384
                logger.info(
                    "Loaded embedding model '%s' (dim=%s)", self.model_name, self._dimension
                )
                return model
            except Exception as exc:
                logger.error("Failed to load SentenceTransformer '%s': %s", self.model_name, exc)
                raise EmbeddingError(
                    f"Could not load embedding model '{self.model_name}': {exc}"
                ) from exc

    @property
    def dimension(self) -> int:
        return self._dimension or 384

    async def embed(self, text: str) -> List[float]:
        results = await self.embed_batch([text])
        if not results:
            raise EmbeddingError("Empty embedding result generated.")
        return results[0]

    async def embed_batch(self, texts: List[str], batch_size: int | None = None) -> List[List[float]]:
        if not texts:
            return []
        model = await self._ensure_model_loaded()
        bs = batch_size or self.batch_size

        def _run_batch():
            return model.encode(
                texts,
                batch_size=bs,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )

        loop = asyncio.get_running_loop()
        vectors = await loop.run_in_executor(None, _run_batch)
        return [[float(v) for v in row] for row in vectors]


@lru_cache(maxsize=1)
def get_local_embedding() -> LocalEmbedding:
    return LocalEmbedding()
