import io
import os
import re
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from PIL import Image
import pytest

from app.core.config import Settings, get_settings
from app.core.exceptions import DocumentProcessingError, LLMError
from app.integrations.documents.base import ParsedPage
from app.integrations.documents.image_parser import ImageParser
from app.integrations.documents.pdf_parser import PDFParser
from app.integrations.llm.factory import LLMFactory, get_llm
from app.integrations.ocr import (
    HuggingFaceOCR,
    HuggingFaceOCRService,
    OCRResult,
    OCRService,
    normalize_ocr_output,
)


# ==============================================================================
# 1. Environment Variable and Architecture Audit Tests
# ==============================================================================

def test_no_direct_env_access_outside_config_py():
    """Verify that no backend/app Python file uses os.getenv, os.environ, or dotenv outside config.py."""
    app_dir = Path(__file__).resolve().parent.parent / "app"
    forbidden_patterns = [
        re.compile(r"\bos\.getenv\s*\("),
        re.compile(r"\bos\.environ\s*\["),
        re.compile(r"\bos\.environ\.get\s*\("),
        re.compile(r"\bload_dotenv\s*\("),
    ]

    violations = []
    for py_file in app_dir.rglob("*.py"):
        # config.py is the single allowed source of truth for environment loading
        if py_file.name == "config.py":
            continue

        content = py_file.read_text(encoding="utf-8")
        for pat in forbidden_patterns:
            matches = pat.findall(content)
            if matches:
                violations.append(f"{py_file.name}: matched forbidden pattern '{pat.pattern}'")

    assert not violations, f"Direct environment access violations found: {violations}"


def test_env_example_contains_all_settings_fields():
    """Verify every Settings field in config.py is documented in .env.example."""
    project_root = Path(__file__).resolve().parent.parent.parent
    env_example_path = project_root / ".env.example"
    assert env_example_path.exists(), ".env.example must exist at project root"

    env_example_content = env_example_path.read_text(encoding="utf-8")
    env_example_vars = set()
    for line in env_example_content.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            var_name = line.split("=")[0].strip()
            env_example_vars.add(var_name)

    # Get all aliases from Settings
    settings_fields = Settings.model_fields
    settings_aliases = {
        (field.alias or name)
        for name, field in settings_fields.items()
    }

    # Verify each Settings alias is in .env.example
    missing_in_env_example = settings_aliases - env_example_vars
    assert not missing_in_env_example, (
        f"The following Settings aliases are missing from .env.example: {missing_in_env_example}"
    )


def test_docker_compose_backend_contains_all_settings():
    """Verify docker-compose backend service environment defines all required Settings."""
    project_root = Path(__file__).resolve().parent.parent.parent
    compose_path = project_root / "docker-compose.yml"
    assert compose_path.exists(), "docker-compose.yml must exist at project root"

    content = compose_path.read_text(encoding="utf-8")
    # Backend environment section
    assert "GOOGLE_API_KEY" in content
    assert "OLLAMA_API_KEY" in content
    assert "HF_API_TOKEN" in content
    assert "HF_OCR_MODEL" in content
    assert "DATABASE_URL" in content
    assert "JWT_SECRET_KEY" in content
    assert "EMBEDDING_PROVIDER" in content

    # Frontend must not have backend secrets
    frontend_section = content.split("frontend:")[-1]
    assert "HF_API_TOKEN" not in frontend_section
    assert "OLLAMA_API_KEY" not in frontend_section
    assert "GOOGLE_API_KEY" not in frontend_section
    assert "JWT_SECRET_KEY" not in frontend_section


def test_no_local_torch_or_sentence_transformers_dependencies():
    """Verify that PyTorch and sentence-transformers are completely absent from requirements.txt and Dockerfile."""
    backend_dir = Path(__file__).resolve().parent.parent
    requirements_path = backend_dir / "requirements.txt"
    dockerfile_path = backend_dir / "Dockerfile"

    req_content = requirements_path.read_text(encoding="utf-8")
    assert "sentence-transformers" not in req_content.lower()
    assert "torch" not in req_content.lower()

    dockerfile_content = dockerfile_path.read_text(encoding="utf-8")
    assert "torch" not in dockerfile_content.lower()
    assert "sentence-transformers" not in dockerfile_content.lower()


# ==============================================================================
# 2. Configuration Validation Tests
# ==============================================================================

def test_missing_database_url_raises_validation_error(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(Exception) as exc_info:
        Settings(_env_file=None)
    assert "database_url" in str(exc_info.value).lower() or "validation error" in str(exc_info.value).lower()


def test_missing_jwt_secret_key_raises_validation_error(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(Exception) as exc_info:
        Settings(_env_file=None)
    assert "jwt_secret_key" in str(exc_info.value).lower() or "validation error" in str(exc_info.value).lower()


def test_invalid_llm_provider_raises_configuration_error(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "unsupported_llm")
    with pytest.raises(Exception) as exc_info:
        Settings(_env_file=None)
    assert "Unsupported LLM provider" in str(exc_info.value)


def test_gemini_without_google_api_key_fails(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GOOGLE_API_KEY", "")
    with pytest.raises(Exception) as exc_info:
        Settings(_env_file=None)
    assert "GOOGLE_API_KEY" in str(exc_info.value)


def test_ollama_without_api_key_fails(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_API_KEY", "")
    monkeypatch.setenv("OLLAMA_BASE_URL", "https://ollama.com")
    with pytest.raises(Exception) as exc_info:
        Settings(_env_file=None)
    assert "OLLAMA_API_KEY" in str(exc_info.value)


def test_ollama_without_base_url_fails(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_API_KEY", "test-key")
    monkeypatch.setenv("OLLAMA_BASE_URL", "")
    with pytest.raises(Exception) as exc_info:
        Settings(_env_file=None)
    assert "OLLAMA_BASE_URL" in str(exc_info.value)


def test_hf_ocr_missing_token_raises_document_processing_error():
    ocr = HuggingFaceOCRService(api_token="")
    img = Image.new("RGB", (10, 10), color="white")
    with pytest.raises(DocumentProcessingError) as exc_info:
        ocr.extract_text(img, page_number=1)
    assert "HF_API_TOKEN" in str(exc_info.value)


# ==============================================================================
# 3. LangChain LLM Architecture Tests
# ==============================================================================

def test_gemini_factory_returns_chat_google_generative_ai():
    from langchain_google_genai import ChatGoogleGenerativeAI
    llm = LLMFactory.get_chat_model(provider="gemini", model_name="gemini-3.6-flash")
    assert isinstance(llm, ChatGoogleGenerativeAI)
    assert "gemini-3.6-flash" in llm.model


def test_ollama_factory_returns_chat_ollama():
    from langchain_ollama import ChatOllama
    llm = LLMFactory.get_chat_model(provider="ollama", model_name="gpt-oss:120b")
    assert isinstance(llm, ChatOllama)
    assert llm.model == "gpt-oss:120b"
    assert "https://ollama.com" in llm.base_url
    assert "Authorization" in llm.client_kwargs["headers"]


def test_provider_model_mismatch_raises_llm_error():
    with pytest.raises(LLMError) as exc_info:
        LLMFactory.get_chat_model(provider="gemini", model_name="gpt-oss:120b")
    assert "cannot be used with provider 'gemini'" in str(exc_info.value)


def test_unsupported_model_raises_llm_error():
    with pytest.raises(LLMError) as exc_info:
        LLMFactory.get_chat_model(model_name="gemini-2.5-flash")
    assert "Unsupported model" in str(exc_info.value)


# ==============================================================================
# 4. Hugging Face Remote OCR Tests
# ==============================================================================

def test_hf_ocr_bearer_header_and_model_sent():
    ocr = HuggingFaceOCRService(api_token="hf_test_secret", model_id="Qwen/Qwen2.5-VL-72B-Instruct")
    img = Image.new("RGB", (50, 50), color="white")

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"role": "assistant", "content": "# Extracted Title\n\nPage body."}}]
    }

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        result = ocr.extract_text(img, page_number=1)
        assert result.text == "# Extracted Title\n\nPage body."
        assert result.format == "markdown"

        headers = mock_post.call_args.kwargs.get("headers", {})
        assert headers.get("Authorization") == "Bearer hf_test_secret"
        payload = mock_post.call_args.kwargs.get("json", {})
        assert payload.get("model") == "Qwen/Qwen2.5-VL-72B-Instruct"


def test_hf_ocr_error_status_codes():
    ocr = HuggingFaceOCRService(api_token="hf_test_secret")
    img = Image.new("RGB", (50, 50), color="white")

    for status_code, expected_snippet in [
        (400, "HTTP 400"),
        (401, "authentication failed"),
        (404, "not found or is not hosted"),
        (429, "rate limit"),
        (503, "currently loading"),
    ]:
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = status_code
        mock_resp.text = f"Error {status_code}"

        with patch("httpx.Client.post", return_value=mock_resp):
            with pytest.raises(DocumentProcessingError) as exc_info:
                ocr.extract_text(img, page_number=1)
            assert expected_snippet.lower() in str(exc_info.value).lower()


def test_digital_pdf_bypasses_ocr(tmp_path):
    mock_ocr = MagicMock(spec=HuggingFaceOCRService)
    parser = PDFParser(ocr=mock_ocr)

    mock_page = MagicMock()
    mock_page.extract_text.return_value = (
        "Operating Systems: Process Management and CPU Scheduling Algorithms."
    )

    with patch("app.integrations.documents.pdf_parser.PdfReader") as mock_reader_cls:
        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]
        mock_reader_cls.return_value = mock_reader

        pdf_path = tmp_path / "digital.pdf"
        pages = parser.parse_file(str(pdf_path))

        assert len(pages) == 1
        assert pages[0].is_ocr is False
        mock_ocr.extract_text.assert_not_called()


def test_scanned_pdf_invokes_hf_ocr(tmp_path):
    mock_ocr = MagicMock(spec=HuggingFaceOCRService)
    mock_ocr.extract_text.return_value = OCRResult(
        text="# Scanned Notes\nKey points of relational algebra.",
        page_number=1,
    )
    parser = PDFParser(ocr=mock_ocr)

    mock_page = MagicMock()
    mock_page.extract_text.return_value = ""  # Scanned page
    mock_page.images = []

    dummy_image = Image.new("RGB", (50, 50), color="white")

    with patch("app.integrations.documents.pdf_parser.PdfReader") as mock_reader_cls, \
         patch("pdf2image.convert_from_path", return_value=[dummy_image]):
        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]
        mock_reader_cls.return_value = mock_reader

        pdf_path = tmp_path / "scanned.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 dummy")
        pages = parser.parse_file(str(pdf_path))

        assert len(pages) == 1
        assert pages[0].is_ocr is True
        mock_ocr.extract_text.assert_called_once()
