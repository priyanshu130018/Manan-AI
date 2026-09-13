import asyncio
import re
from google import genai
from google.genai import types

from app.core.config import get_settings
from app.core.logging import LoggerFactory
from app.core.exceptions import LLMError, EmbeddingError, RateLimitError

logger = LoggerFactory.create_logger("GeminiClient")

_RETRY_DELAY_RE = re.compile(r"retry in ([0-9.]+)s", re.IGNORECASE)


def _extract_retry_seconds(err: Exception, default: float) -> float:
    m = _RETRY_DELAY_RE.search(str(err))
    if m:
        try:
            return float(m.group(1)) + 0.5
        except ValueError:
            pass
    return default


class GeminiClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._settings = settings
        self._llm_model = settings.gemini_model
        self._embedding_model = settings.embedding_model
        self._client = genai.Client(api_key=settings.google_api_key).aio

    async def generate_text(
        self,
        prompt: str,
        system_instruction: str | None = None,
        model_name: str | None = None,
    ) -> str:
        """Generate content using configured or overridden Gemini LLM model."""
        try:
            config = None
            if system_instruction:
                config = types.GenerateContentConfig(system_instruction=system_instruction)

            selected_model = model_name or self._llm_model
            response = await self._client.models.generate_content(
                model=selected_model,
                contents=prompt,
                config=config,
            )
            if not response or not response.text:
                raise LLMError("Empty response received from Gemini.")
            return response.text.strip()
        except Exception as e:
            err_str = str(e)
            logger.exception("Gemini text generation failed: %s", err_str)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "rate limit" in err_str.lower():
                retry_sec = _extract_retry_seconds(e, default=30.0)
                raise RateLimitError(
                    f"Gemini quota temporarily exhausted. Please wait {int(retry_sec)}s or switch to a different AI model in Settings.",
                    retry_after=retry_sec,
                )
            raise LLMError(f"AI response generation failed: {err_str}")

    async def _embed_one(self, text: str, retries: int = 4) -> list[float]:
        attempt = 0
        while True:
            try:
                response = await self._client.models.embed_content(
                    model=self._embedding_model,
                    contents=text,
                )
                return response.embeddings[0].values
            except Exception as e:
                attempt += 1
                delay = _extract_retry_seconds(e, default=2**attempt)
                if attempt > retries:
                    logger.exception("Embedding failed after %s attempts: %s", retries, str(e))
                    raise EmbeddingError(f"Embedding failed: {str(e)}")
                logger.warning(
                    "Embedding hit rate limit on attempt %s, retrying in %.1fs — %s",
                    attempt,
                    delay,
                    str(e)[:200],
                )
                await asyncio.sleep(delay)

    async def embed_text(self, text: str) -> list[float]:
        """Generate vector embedding for a single text chunk with retry/backoff."""
        return await self._embed_one(text)

    async def embed_batch(self, texts: list[str], batch_size: int = 10) -> list[list[float]]:
        """Generate vector embeddings for a batch of text chunks with retry + pacing."""
        if not texts:
            return []

        all_embeddings: list[list[float]] = []
        try:
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                attempt = 0
                retries = 4
                while True:
                    try:
                        response = await self._client.models.embed_content(
                            model=self._embedding_model,
                            contents=batch,
                        )
                        for emb in response.embeddings:
                            all_embeddings.append(emb.values)
                        break
                    except Exception as e:
                        attempt += 1
                        delay = _extract_retry_seconds(e, default=2**attempt)
                        if attempt > retries:
                            raise
                        logger.warning(
                            "Batch %s embedding rate-limit on attempt %s, retrying in %.1fs",
                            i // batch_size + 1,
                            attempt,
                            delay,
                        )
                        await asyncio.sleep(delay)

                if i + batch_size < len(texts):
                    await asyncio.sleep(0.6)
            return all_embeddings
        except Exception as e:
            logger.warning(
                "Batch embedding failed after retries (%s), falling back to sequential with retry.",
                str(e),
            )
            fallback: list[list[float]] = []
            for idx, t in enumerate(texts):
                single = await self._embed_one(t)
                fallback.append(single)
                if idx % 5 == 4 and idx < len(texts) - 1:
                    await asyncio.sleep(1.0)
            return fallback


class GeminiLLM:
    def __init__(self, client: GeminiClient | None = None, model_name: str | None = None) -> None:
        self._client = client or GeminiClient()
        self._model_name = model_name

    async def generate(
        self,
        prompt: str,
        system_instruction: str | None = None,
        model_name: str | None = None,
    ) -> str:
        return await self._client.generate_text(
            prompt=prompt,
            system_instruction=system_instruction,
            model_name=model_name or self._model_name,
        )


class GeminiEmbedding:
    def __init__(self, client: GeminiClient | None = None) -> None:
        self._client = client or GeminiClient()

    async def embed(self, text: str) -> list[float]:
        return await self._client.embed_text(text)

    async def embed_batch(self, texts: list[str], batch_size: int = 50) -> list[list[float]]:
        return await self._client.embed_batch(texts, batch_size=batch_size)
