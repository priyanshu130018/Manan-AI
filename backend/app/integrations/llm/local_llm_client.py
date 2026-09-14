"""Local HuggingFace / transformers LLM client — drop-in replacement for GeminiLLM.

Loads a causal language model directly from a local path or HuggingFace Hub ID
and runs inference in-process (CPU or CUDA/MPS when available).

Compatible interface with GeminiLLM so it can be injected into ChatService or
StudyService without modifying those classes:

    from app.integrations.llm.local_llm_client import LocalLLM
    llm = LocalLLM(model_id="mistralai/Mistral-7B-Instruct-v0.3")
    chat_service = ChatService(llm=llm)

Requirements (not in core requirements.txt — install as needed):
    pip install transformers torch accelerate

Configuration:
    model_id      HuggingFace Hub model ID or local directory path.
    max_new_tokens Maximum tokens to generate (default: 512).
    temperature   Sampling temperature (default: 0.7, set ≤0 for greedy decoding).
    device_map    Device placement passed to from_pretrained ('auto', 'cpu', etc.).
    load_in_8bit  Quantise model weights to 8-bit using bitsandbytes (needs GPU).
    load_in_4bit  Quantise model weights to 4-bit using bitsandbytes (needs GPU).

Notes:
    - The model is loaded lazily on first call to generate() to avoid blocking
      application startup.
    - Inference runs in a thread-pool executor so the event loop is not blocked.
    - For very large models (>13 B params), quantisation or Ollama is recommended.
"""

from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Any

from app.core.logging import LoggerFactory

logger = LoggerFactory.create_logger("LocalLLMClient")

_DEFAULT_MODEL = "HuggingFaceTB/SmolLM2-1.7B-Instruct"
_DEFAULT_MAX_NEW_TOKENS = 512
_DEFAULT_TEMPERATURE = 0.7


class LocalLLMClient:
    """Async wrapper around a HuggingFace transformers text-generation pipeline."""

    def __init__(
        self,
        model_id: str = _DEFAULT_MODEL,
        max_new_tokens: int = _DEFAULT_MAX_NEW_TOKENS,
        temperature: float = _DEFAULT_TEMPERATURE,
        device_map: str = "auto",
        load_in_8bit: bool = False,
        load_in_4bit: bool = False,
        pipeline_kwargs: dict[str, Any] | None = None,
    ) -> None:
        self.model_id = model_id
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.device_map = device_map
        self.load_in_8bit = load_in_8bit
        self.load_in_4bit = load_in_4bit
        self._pipeline_kwargs = pipeline_kwargs or {}
        self._pipeline: Any = None
        self._load_lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Lazy model loading
    # ------------------------------------------------------------------

    async def _ensure_pipeline(self) -> Any:
        """Load the transformers pipeline on first use (thread-safe)."""
        if self._pipeline is not None:
            return self._pipeline
        async with self._load_lock:
            if self._pipeline is not None:
                return self._pipeline
            logger.info("Loading local LLM: %s (device_map=%s)", self.model_id, self.device_map)
            try:
                from transformers import pipeline, AutoTokenizer  # type: ignore
            except ImportError as exc:
                raise RuntimeError(
                    "transformers is not installed. "
                    "Install with: pip install transformers torch accelerate"
                ) from exc

            quantization_config: dict[str, Any] = {}
            if self.load_in_4bit or self.load_in_8bit:
                try:
                    from transformers import BitsAndBytesConfig  # type: ignore

                    quantization_config["quantization_config"] = BitsAndBytesConfig(
                        load_in_8bit=self.load_in_8bit,
                        load_in_4bit=self.load_in_4bit,
                    )
                except ImportError:
                    logger.warning(
                        "bitsandbytes not installed — quantisation skipped. "
                        "Install with: pip install bitsandbytes"
                    )

            def _load() -> Any:
                tokenizer = AutoTokenizer.from_pretrained(self.model_id)
                pipe = pipeline(
                    "text-generation",
                    model=self.model_id,
                    tokenizer=tokenizer,
                    device_map=self.device_map,
                    **quantization_config,
                    **self._pipeline_kwargs,
                )
                return pipe

            loop = asyncio.get_event_loop()
            self._pipeline = await loop.run_in_executor(None, _load)
            logger.info("Local LLM loaded: %s", self.model_id)
            return self._pipeline

    # ------------------------------------------------------------------
    # Text generation
    # ------------------------------------------------------------------

    async def generate(
        self,
        prompt: str,
        system_instruction: str | None = None,
        max_new_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        """Generate text from a prompt.

        If the loaded model supports a chat template (instruct models), the
        prompt + optional system instruction are wrapped in the standard
        conversation format automatically. Plain-completion models receive the
        raw prompt.

        Args:
            prompt:            The user's input text.
            system_instruction: Optional system-level preamble.
            max_new_tokens:    Override instance-level max_new_tokens.
            temperature:       Override instance-level temperature.

        Returns:
            The generated text as a plain string (no prompt echo).
        """
        pipe = await self._ensure_pipeline()
        tokens = max_new_tokens or self.max_new_tokens
        temp = temperature if temperature is not None else self.temperature

        gen_kwargs: dict[str, Any] = {
            "max_new_tokens": tokens,
            "do_sample": temp > 0,
        }
        if temp > 0:
            gen_kwargs["temperature"] = temp

        # Build input — use chat template if available
        tokenizer = pipe.tokenizer
        if hasattr(tokenizer, "apply_chat_template") and tokenizer.chat_template:
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})
            input_text = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        else:
            if system_instruction:
                input_text = f"{system_instruction}\n\n{prompt}"
            else:
                input_text = prompt

        def _run() -> str:
            outputs = pipe(input_text, **gen_kwargs)
            raw: str = outputs[0]["generated_text"]
            # Strip the echoed input — transformers pipelines include it by default.
            if raw.startswith(input_text):
                raw = raw[len(input_text):]
            return raw.strip()

        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(None, _run)
            logger.debug(
                "LocalLLMClient.generate model=%s tokens_out=%d",
                self.model_id,
                len(result.split()),
            )
            return result
        except Exception as exc:
            logger.exception("LocalLLMClient.generate failed: %s", exc)
            raise RuntimeError(f"Local LLM generation failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Embed interface (not supported — use LocalEmbedding instead)
    # ------------------------------------------------------------------

    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError(
            "LocalLLMClient does not support embeddings. "
            "Use app.integrations.embeddings.LocalEmbedding for that."
        )


class LocalLLM:
    """High-level wrapper with the same interface as GeminiLLM.

    Drop this anywhere a GeminiLLM is accepted:

        llm = LocalLLM(model_id="mistralai/Mistral-7B-Instruct-v0.3")
        chat_service = ChatService(llm=llm)
    """

    def __init__(
        self,
        model_id: str = _DEFAULT_MODEL,
        max_new_tokens: int = _DEFAULT_MAX_NEW_TOKENS,
        temperature: float = _DEFAULT_TEMPERATURE,
        device_map: str = "auto",
        load_in_8bit: bool = False,
        load_in_4bit: bool = False,
        client: LocalLLMClient | None = None,
    ) -> None:
        self._client = client or LocalLLMClient(
            model_id=model_id,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            device_map=device_map,
            load_in_8bit=load_in_8bit,
            load_in_4bit=load_in_4bit,
        )

    @property
    def client(self) -> LocalLLMClient:
        return self._client

    async def generate(
        self,
        prompt: str,
        system_instruction: str | None = None,
    ) -> str:
        """Generate a response — same signature as GeminiLLM.generate()."""
        return await self._client.generate(
            prompt=prompt,
            system_instruction=system_instruction,
        )


@lru_cache(maxsize=1)
def get_local_llm(
    model_id: str = _DEFAULT_MODEL,
    max_new_tokens: int = _DEFAULT_MAX_NEW_TOKENS,
) -> LocalLLM:
    """Cached singleton — avoids loading the model more than once per process."""
    return LocalLLM(model_id=model_id, max_new_tokens=max_new_tokens)
