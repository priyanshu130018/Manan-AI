import base64
import io
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union
import httpx
from PIL import Image

from app.core.config import get_settings
from app.core.exceptions import DocumentProcessingError
from app.core.logging import LoggerFactory

logger = LoggerFactory.create_logger("HuggingFaceOCRService")


@dataclass
class OCRResult:
    text: str
    page_number: int = 1
    confidence: float = 0.0
    format: str = "markdown"


def normalize_ocr_output(text: str) -> str:
    """
    Clean and structure raw OCR / VLM text into standard Markdown.
    Preserves headings, tables, bullet points, and code blocks while removing
    extraneous whitespace, non-printable characters, and empty blocks.
    """
    if not text:
        return ""

    # Replace carriage returns and standard null/escape artifacts
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", cleaned)

    # Normalize excessive blank lines (more than 2 -> 2)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    # Strip trailing whitespace on each line
    lines = [line.rstrip() for line in cleaned.split("\n")]
    result = "\n".join(lines).strip()

    return result


class HuggingFaceOCRService:
    """
    OCR service calling the Hugging Face Hosted Inference API over HTTPS
    for vision-language / OCR models (e.g. Qwen/Qwen2.5-VL-72B-Instruct).
    Does NOT download or execute model weights locally.
    """

    def __init__(
        self,
        api_token: Optional[str] = None,
        model_id: Optional[str] = None,
        timeout: float = 60.0,
    ) -> None:
        settings = get_settings()
        self.api_token = api_token or settings.hf_api_token
        self.model_id = model_id or settings.hf_ocr_model
        self.timeout = timeout

    @property
    def is_available(self) -> bool:
        """Returns True if Hugging Face API token is configured."""
        return bool(self.api_token and self.api_token.strip())

    def _image_to_bytes(self, image: Union[Image.Image, str, bytes, Path]) -> bytes:
        if isinstance(image, Image.Image):
            buf = io.BytesIO()
            image.convert("RGB").save(buf, format="PNG")
            return buf.getvalue()
        elif isinstance(image, (str, Path)):
            return Path(image).read_bytes()
        elif isinstance(image, bytes):
            return image
        raise DocumentProcessingError(f"Unsupported image input type: {type(image)}")

    def extract_text(
        self,
        image: Union[Image.Image, str, bytes, Path],
        page_number: int = 1,
    ) -> OCRResult:
        """
        Send image to Hugging Face Hosted Inference API and return normalized OCR result.
        """
        if not self.api_token or not self.api_token.strip():
            raise DocumentProcessingError(
                "Hugging Face API token (HF_API_TOKEN) is not configured. "
                "Please set HF_API_TOKEN in environment variables."
            )

        img_bytes = self._image_to_bytes(image)
        b64_img = base64.b64encode(img_bytes).decode("utf-8")
        data_uri = f"data:image/png;base64,{b64_img}"

        headers = {
            "Authorization": f"Bearer {self.api_token.strip()}",
            "Content-Type": "application/json",
        }

        # 1. Try OpenAI-compatible Chat Completions on Hugging Face Router
        router_url = "https://router.huggingface.co/v1/chat/completions"
        payload = {
            "model": self.model_id,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract all text and structure from this document as Markdown."},
                        {"type": "image_url", "image_url": {"url": data_uri}},
                    ],
                }
            ],
            "max_tokens": 2048,
        }

        logger.info(
            "Calling Hugging Face Hosted Inference API for page %d (model=%s)",
            page_number,
            self.model_id,
        )

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(router_url, headers=headers, json=payload)

                # If router returns 200 OK
                if res.status_code == 200:
                    data = res.json()
                    choices = data.get("choices", [])
                    if choices and "message" in choices[0] and "content" in choices[0]["message"]:
                        raw_text = choices[0]["message"]["content"]
                        normalized = normalize_ocr_output(raw_text)
                        return OCRResult(
                            text=normalized,
                            page_number=page_number,
                            confidence=0.95 if normalized else 0.0,
                            format="markdown",
                        )

                # 2. Fallback to direct model inference endpoint if router returned 404/400
                if res.status_code in (404, 400, 422):
                    direct_url = f"https://router.huggingface.co/hf-inference/models/{self.model_id}"
                    direct_headers = {
                        "Authorization": f"Bearer {self.api_token.strip()}",
                    }
                    direct_res = client.post(
                        direct_url,
                        headers=direct_headers,
                        content=img_bytes,
                    )
                    if direct_res.status_code == 200:
                        content_type = direct_res.headers.get("content-type", "")
                        if "json" in content_type:
                            data = direct_res.json()
                            if isinstance(data, list) and len(data) > 0:
                                item = data[0]
                                if isinstance(item, dict):
                                    raw_text = item.get("generated_text", item.get("text", str(item)))
                                else:
                                    raw_text = str(item)
                            elif isinstance(data, dict):
                                raw_text = data.get("generated_text", data.get("text", str(data)))
                            else:
                                raw_text = str(data)
                        else:
                            raw_text = direct_res.text
                        normalized = normalize_ocr_output(raw_text)
                        return OCRResult(
                            text=normalized,
                            page_number=page_number,
                            confidence=0.95 if normalized else 0.0,
                            format="markdown",
                        )
                    res = direct_res

                # Handle HTTP errors with clear diagnostics
                if res.status_code == 400:
                    raise DocumentProcessingError(
                        f"Hugging Face OCR API request failed (HTTP 400): {res.text}"
                    )
                elif res.status_code == 401:
                    raise DocumentProcessingError(
                        "Hugging Face API authentication failed (HTTP 401). Verify that HF_API_TOKEN is valid."
                    )
                elif res.status_code == 404:
                    raise DocumentProcessingError(
                        f"Model '{self.model_id}' was not found or is not hosted on Hugging Face Serverless Inference API (HTTP 404). "
                        f"Ensure the model is deployed on a dedicated Hugging Face Inference Endpoint or that HF_OCR_MODEL is set to a supported model."
                    )
                elif res.status_code == 429:
                    raise DocumentProcessingError(
                        "Hugging Face Inference API rate limit reached (HTTP 429). Please wait before retrying."
                    )
                elif res.status_code == 503:
                    raise DocumentProcessingError(
                        f"Hugging Face model '{self.model_id}' is currently loading (HTTP 503): {res.text}"
                    )
                else:
                    raise DocumentProcessingError(
                        f"Hugging Face OCR API request failed (HTTP {res.status_code}): {res.text}"
                    )

        except httpx.RequestError as exc:
            logger.warning("Network error calling Hugging Face OCR API: %s", exc)
            raise DocumentProcessingError(f"Network error connecting to Hugging Face OCR API: {exc}") from exc
        except Exception as exc:
            if isinstance(exc, DocumentProcessingError):
                raise
            logger.warning("Hugging Face OCR processing error: %s", exc)
            raise DocumentProcessingError(f"Hugging Face OCR processing error: {exc}") from exc

    def extract_from_document(self, file_path: Union[str, Path]) -> list[OCRResult]:
        """
        Extract text from all pages of a document using pdf2image + Hugging Face OCR API.
        """
        path = Path(file_path)
        if not path.exists():
            raise DocumentProcessingError(f"Document file not found: {file_path}")

        results: list[OCRResult] = []
        try:
            from pdf2image import convert_from_path
            images = convert_from_path(str(path))
            for idx, img in enumerate(images, start=1):
                res = self.extract_text(img, page_number=idx)
                if res.text:
                    results.append(res)
        except Exception as e:
            if isinstance(e, DocumentProcessingError):
                raise
            logger.warning("extract_from_document failed with pdf2image for %s: %s", file_path, str(e))
            raise DocumentProcessingError(f"Failed to extract document pages for OCR: {e}")

        return results


# Aliases for compatibility
HuggingFaceOCR = HuggingFaceOCRService
OCRService = HuggingFaceOCRService
