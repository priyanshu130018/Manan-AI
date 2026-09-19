import asyncio
from typing import Any, List, Optional
import httpx
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError, LLMError, RateLimitError
from app.core.logging import LoggerFactory

logger = LoggerFactory.create_logger("QwenClient")


class QwenClient:
    """Async client for Alibaba Cloud Model Studio (Qwen) OpenAI-compatible Chat Completions API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 60.0,
    ) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.qwen_api_key or ""
        self._base_url = (
            base_url
            or settings.qwen_base_url
            or "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
        ).rstrip("/")
        self._model = model or settings.qwen_model or "qwen3.8-27b"
        self._timeout = timeout

    async def aclose(self) -> None:
        """No persistent resources to close."""
        pass

    async def generate_messages(
        self,
        messages: List[dict[str, str]],
        model_name: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        """Send chat messages to Qwen OpenAI-compatible API and return assistant text response."""
        if not self._api_key:
            raise AuthenticationError(
                "Qwen API key is not configured. Please set QWEN_API_KEY in environment."
            )

        selected_model = model_name or self._model
        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": selected_model,
            "messages": messages,
            "temperature": temperature,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, headers=headers, json=payload)

            if response.status_code == 401 or response.status_code == 403:
                logger.error("Qwen API authentication failed (status %d)", response.status_code)
                raise AuthenticationError("Invalid Qwen API key or unauthorized request.")

            if response.status_code == 429:
                logger.warning("Qwen API quota/rate limit exceeded (status 429)")
                raise RateLimitError(
                    "Qwen API quota or rate limit temporarily exceeded. Please try again shortly.",
                    retry_after=30.0,
                )

            if response.status_code >= 400:
                err_text = response.text
                try:
                    err_json = response.json()
                    err_msg = err_json.get("error", {}).get("message") or err_text
                except Exception:
                    err_msg = err_text
                logger.error("Qwen API error (status %d): %s", response.status_code, err_msg)
                raise LLMError(
                    f"Qwen API error ({response.status_code}): {err_msg}",
                    provider="qwen",
                    model=selected_model,
                )

            data = response.json()
            choices = data.get("choices", [])
            if not choices or not choices[0].get("message", {}).get("content"):
                raise LLMError(
                    "Empty response received from Qwen API.",
                    provider="qwen",
                    model=selected_model,
                )

            return choices[0]["message"]["content"].strip()

        except (AuthenticationError, RateLimitError, LLMError):
            raise
        except httpx.TimeoutException as e:
            logger.error("Qwen API request timed out: %s", e)
            raise LLMError(
                "Qwen API request timed out. Please try again.",
                provider="qwen",
                model=selected_model,
            ) from e
        except httpx.RequestError as e:
            logger.error("Qwen API network error: %s", e)
            raise LLMError(
                f"Qwen API connection error: {str(e)}",
                provider="qwen",
                model=selected_model,
            ) from e
        except Exception as e:
            logger.exception("Unexpected error during Qwen generation: %s", e)
            raise LLMError(
                f"Qwen generation failed: {str(e)}",
                provider="qwen",
                model=selected_model,
            ) from e

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> str:
        """Convenience method to generate text from a single prompt and optional system instruction."""
        msgs = []
        if system_instruction:
            msgs.append({"role": "system", "content": system_instruction})
        msgs.append({"role": "user", "content": prompt})
        return await self.generate_messages(msgs, model_name=model_name)

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> str:
        """Alias for generate() for consistency across clients."""
        return await self.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            model_name=model_name,
        )


class ChatQwen:
    """LangChain-compatible chat model wrapper for Qwen."""

    def __init__(
        self,
        client: Optional[QwenClient] = None,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
    ) -> None:
        if client:
            self._client = client
        else:
            self._client = QwenClient(api_key=api_key, base_url=base_url, model=model_name)
        self.model_name = model_name or self._client._model
        self.temperature = temperature

    async def ainvoke(
        self, input_messages: List[BaseMessage] | List[Any], **kwargs: Any
    ) -> AIMessage:
        """Process LangChain BaseMessage list directly into Qwen Chat Completions API."""
        formatted_messages: List[dict[str, str]] = []
        for msg in input_messages:
            if isinstance(msg, SystemMessage):
                formatted_messages.append({"role": "system", "content": str(msg.content)})
            elif isinstance(msg, HumanMessage):
                formatted_messages.append({"role": "user", "content": str(msg.content)})
            elif isinstance(msg, AIMessage):
                formatted_messages.append({"role": "assistant", "content": str(msg.content)})
            elif isinstance(msg, dict):
                role = msg.get("role", "user")
                if role not in {"system", "user", "assistant"}:
                    role = "user"
                formatted_messages.append({"role": role, "content": str(msg.get("content", ""))})
            else:
                formatted_messages.append(
                    {"role": "user", "content": str(getattr(msg, "content", msg))}
                )

        text = await self._client.generate_messages(
            messages=formatted_messages,
            model_name=self.model_name,
            temperature=self.temperature,
        )
        return AIMessage(content=text)

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
    ) -> str:
        return await self._client.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            model_name=self.model_name,
        )
