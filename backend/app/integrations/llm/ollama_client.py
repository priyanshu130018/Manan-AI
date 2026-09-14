"""Ollama LLM client — drop-in replacement for GeminiLLM / GeminiClient.

Wraps the Ollama HTTP API (https://github.com/ollama/ollama) running locally
at http://localhost:11434 (or a custom base URL).

Compatible interface with GeminiLLM / GeminiClient so it can be injected
into ChatService or StudyService without changing those classes:

    from app.integrations.llm.ollama_client import OllamaLLM
    llm = OllamaLLM(model="llama3.2")
    chat_service = ChatService(llm=llm)

Configuration (via .env or Settings):
    OLLAMA_BASE_URL   Base URL for Ollama (default: http://localhost:11434)
    OLLAMA_MODEL      Model name served by Ollama (default: llama3.2)
    OLLAMA_TIMEOUT    Per-request timeout in seconds (default: 120)
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.core.logging import LoggerFactory

logger = LoggerFactory.create_logger("OllamaClient")

_DEFAULT_BASE_URL = "http://localhost:11434"
_DEFAULT_MODEL = "llama3.2"
_DEFAULT_TIMEOUT = 120.0


class OllamaClient:
    """Low-level async wrapper around the Ollama REST API."""

    def __init__(
        self,
        base_url: str = _DEFAULT_BASE_URL,
        model: str = _DEFAULT_MODEL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._timeout = timeout
        # Shared async client — reused across requests for connection pooling.
        self._http = httpx.AsyncClient(base_url=self.base_url, timeout=self._timeout)

    # ------------------------------------------------------------------
    # Core generation
    # ------------------------------------------------------------------

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> str:
        """Non-streaming text generation via POST /api/generate.

        Args:
            prompt:  The user prompt.
            system:  Optional system-level instruction (prepended context).
            options: Ollama model options dict (temperature, top_p, etc.).

        Returns:
            The model's response as a plain string.

        Raises:
            RuntimeError: If Ollama returns a non-200 status or an error field.
        """
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system
        if options:
            payload["options"] = options

        logger.debug("OllamaClient.generate model=%s prompt_len=%d", self.model, len(prompt))
        response = await self._http.post("/api/generate", json=payload)
        response.raise_for_status()

        body = response.json()
        if "error" in body:
            raise RuntimeError(f"Ollama error: {body['error']}")

        return str(body.get("response", "")).strip()

    async def chat(
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> str:
        """Multi-turn chat via POST /api/chat.

        Args:
            messages: List of {"role": "user"|"assistant", "content": "..."}.
            system:   Optional system message prepended to the conversation.
            options:  Ollama model options dict.

        Returns:
            The assistant's reply as a plain string.
        """
        conversation = []
        if system:
            conversation.append({"role": "system", "content": system})
        conversation.extend(messages)

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": conversation,
            "stream": False,
        }
        if options:
            payload["options"] = options

        logger.debug(
            "OllamaClient.chat model=%s messages=%d", self.model, len(conversation)
        )
        response = await self._http.post("/api/chat", json=payload)
        response.raise_for_status()

        body = response.json()
        if "error" in body:
            raise RuntimeError(f"Ollama error: {body['error']}")

        return str(body.get("message", {}).get("content", "")).strip()

    async def list_models(self) -> list[str]:
        """Return the names of locally available Ollama models."""
        response = await self._http.get("/api/tags")
        response.raise_for_status()
        tags: list[dict[str, Any]] = response.json().get("models", [])
        return [t["name"] for t in tags]

    async def health(self) -> bool:
        """Return True if Ollama is reachable and responding."""
        try:
            response = await self._http.get("/")
            return response.status_code == 200
        except Exception:
            return False

    async def aclose(self) -> None:
        """Close the underlying HTTP client (call on application shutdown)."""
        await self._http.aclose()


class OllamaLLM:
    """High-level wrapper with the same interface as GeminiLLM.

    Drop this in anywhere a GeminiLLM is expected:

        llm = OllamaLLM(model="llama3.2")
        chat_service = ChatService(llm=llm)

    generate() maps to OllamaClient.generate() (single-turn).
    For multi-turn use, call client.chat() directly.
    """

    def __init__(
        self,
        model: str = _DEFAULT_MODEL,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
        client: OllamaClient | None = None,
    ) -> None:
        self._client = client or OllamaClient(
            base_url=base_url, model=model, timeout=timeout
        )

    @property
    def client(self) -> OllamaClient:
        return self._client

    async def generate(
        self,
        prompt: str,
        system_instruction: str | None = None,
        model_name: str | None = None,
    ) -> str:
        """Generate a response — same signature as GeminiLLM.generate()."""
        try:
            return await self._client.generate(prompt=prompt, system=system_instruction)
        except Exception as exc:
            logger.exception("OllamaLLM.generate failed: %s", exc)
            raise RuntimeError(f"Ollama generation failed: {exc}") from exc
