import io
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from PIL import Image
import pytest

from app.core.exceptions import DocumentProcessingError
from app.integrations.documents.base import ParsedPage
from app.integrations.documents.image_parser import ImageParser
from app.integrations.documents.pdf_parser import PDFParser
from app.integrations.ocr import (
    HuggingFaceOCR,
    HuggingFaceOCRService,
    OCRResult,
    OCRService,
    normalize_ocr_output,
)


def test_normalize_ocr_output():
    raw = "\r\n# Chapter 1: Introduction\r\n\r\n\r\n\r\n| Col1 | Col2 |\n|---|---|\n| A | B |\n\x00\x08   \n"
    normalized = normalize_ocr_output(raw)
    assert "# Chapter 1: Introduction" in normalized
    assert "| Col1 | Col2 |" in normalized
    assert "\r" not in normalized
    assert "\x00" not in normalized
    assert "\n\n\n" not in normalized


def test_hf_ocr_aliases():
    assert HuggingFaceOCR is HuggingFaceOCRService
    assert OCRService is HuggingFaceOCRService


def test_hf_ocr_missing_token_raises_error():
    ocr = HuggingFaceOCRService(api_token="")
    img = Image.new("RGB", (100, 100), color="white")
    with pytest.raises(DocumentProcessingError) as exc_info:
        ocr.extract_text(img, page_number=1)
    assert "HF_API_TOKEN" in str(exc_info.value)


def test_hf_ocr_extract_text_router_success():
    ocr = HuggingFaceOCRService(api_token="hf_test_token_123", model_id="Qwen/Qwen2.5-VL-72B-Instruct")
    img = Image.new("RGB", (100, 100), color="white")

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "## Scanned Document\nQuestion 1: Explain ACID properties.",
                }
            }
        ]
    }

    with patch("httpx.Client.post", return_value=mock_response) as mock_post:
        result = ocr.extract_text(img, page_number=3)

        assert isinstance(result, OCRResult)
        assert result.page_number == 3
        assert "## Scanned Document" in result.text
        assert "Question 1: Explain ACID properties." in result.text
        assert result.format == "markdown"

        # Verify authentication header was passed
        mock_post.assert_called_once()
        headers = mock_post.call_args.kwargs.get("headers", {})
        assert headers.get("Authorization") == "Bearer hf_test_token_123"
        payload = mock_post.call_args.kwargs.get("json", {})
        assert payload.get("model") == "Qwen/Qwen2.5-VL-72B-Instruct"


def test_hf_ocr_extract_text_direct_endpoint_success():
    ocr = HuggingFaceOCRService(api_token="hf_test_token_123", model_id="Qwen/Qwen2.5-VL-72B-Instruct")
    img = Image.new("RGB", (100, 100), color="white")

    # First call to router returns 404, second call to direct endpoint returns 200
    mock_router_resp = MagicMock(spec=httpx.Response)
    mock_router_resp.status_code = 404
    mock_router_resp.text = "Not found on router"

    mock_direct_resp = MagicMock(spec=httpx.Response)
    mock_direct_resp.status_code = 200
    mock_direct_resp.headers = {"content-type": "application/json"}
    mock_direct_resp.json.return_value = [{"generated_text": "Text from direct endpoint."}]

    with patch("httpx.Client.post", side_effect=[mock_router_resp, mock_direct_resp]):
        result = ocr.extract_text(img, page_number=1)
        assert "Text from direct endpoint." in result.text


def test_hf_ocr_http_status_codes():
    ocr = HuggingFaceOCRService(api_token="hf_test_token_123", model_id="Qwen/Qwen2.5-VL-72B-Instruct")
    img = Image.new("RGB", (100, 100), color="white")

    for code, snippet in [
        (400, "HTTP 400"),
        (401, "authentication failed"),
        (404, "not found or is not hosted"),
        (429, "rate limit"),
        (503, "currently loading"),
    ]:
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = code
        mock_resp.text = f"Error {code}"

        with patch("httpx.Client.post", return_value=mock_resp):
            with pytest.raises(DocumentProcessingError) as exc_info:
                ocr.extract_text(img, page_number=1)
            assert snippet.lower() in str(exc_info.value).lower()


def test_hf_ocr_network_error_raises_document_processing_error():
    ocr = HuggingFaceOCRService(api_token="hf_test_token_123")
    img = Image.new("RGB", (100, 100), color="white")

    with patch("httpx.Client.post", side_effect=httpx.ConnectError("Connection refused")):
        with pytest.raises(DocumentProcessingError) as exc_info:
            ocr.extract_text(img, page_number=1)
        assert "Network error" in str(exc_info.value)


def test_pdf_parser_normal_text_does_not_call_hf_ocr(tmp_path):
    mock_ocr = MagicMock(spec=HuggingFaceOCRService)
    parser = PDFParser(ocr=mock_ocr)

    pdf_file = tmp_path / "normal_text.pdf"
    # Create mock PdfReader with sufficient extractable text (> 40 chars)
    mock_page = MagicMock()
    mock_page.extract_text.return_value = (
        "Operating Systems and Database Internals. This document contains substantial searchable text."
    )

    with patch("app.integrations.documents.pdf_parser.PdfReader") as mock_reader_cls:
        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]
        mock_reader_cls.return_value = mock_reader

        pages = parser.parse_file(str(pdf_file))

        assert len(pages) == 1
        assert pages[0].page_number == 1
        assert pages[0].is_ocr is False
        assert "Operating Systems" in pages[0].text
        # Ensure OCR API was NOT invoked
        mock_ocr.extract_text.assert_not_called()


def test_pdf_parser_scanned_page_triggers_hf_ocr(tmp_path):
    mock_ocr = MagicMock(spec=HuggingFaceOCRService)
    mock_ocr.extract_text.return_value = OCRResult(
        text="# Scanned Exam Paper\nQuestion 1: Explain ACID properties.",
        page_number=1,
        confidence=0.95,
        format="markdown",
    )
    parser = PDFParser(ocr=mock_ocr)

    pdf_file = tmp_path / "scanned_exam.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 dummy")

    mock_page = MagicMock()
    mock_page.extract_text.return_value = ""  # Scanned page has no extractable text
    mock_page.images = []

    dummy_image = Image.new("RGB", (100, 100), color="white")

    with patch("app.integrations.documents.pdf_parser.PdfReader") as mock_reader_cls, \
         patch("pdf2image.convert_from_path", return_value=[dummy_image]):
        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]
        mock_reader_cls.return_value = mock_reader

        pages = parser.parse_file(str(pdf_file))

        assert len(pages) == 1
        assert pages[0].page_number == 1
        assert pages[0].is_ocr is True
        assert "# Scanned Exam Paper" in pages[0].text
        mock_ocr.extract_text.assert_called_once()


def test_image_parser_uses_hf_ocr(tmp_path):
    mock_ocr = MagicMock(spec=HuggingFaceOCRService)
    mock_ocr.extract_text.return_value = OCRResult(
        text="Diagram: Architecture Overview",
        page_number=1,
        confidence=0.95,
    )
    parser = ImageParser(ocr=mock_ocr)

    img_path = tmp_path / "diagram.png"
    img = Image.new("RGB", (100, 100), color="white")
    img.save(str(img_path))

    pages = parser.parse_file(str(img_path))
    assert len(pages) == 1
    assert pages[0].is_ocr is True
    assert pages[0].text == "Diagram: Architecture Overview"
    mock_ocr.extract_text.assert_called_once()


def test_image_parser_empty_ocr_returns_empty_pages(tmp_path):
    mock_ocr = MagicMock(spec=HuggingFaceOCRService)
    mock_ocr.extract_text.return_value = OCRResult(text="", page_number=1, confidence=0.0)
    parser = ImageParser(ocr=mock_ocr)

    img_path = tmp_path / "blank.png"
    img = Image.new("RGB", (100, 100), color="white")
    img.save(str(img_path))

    pages = parser.parse_file(str(img_path))
    assert len(pages) == 0


def test_document_ingest_scanned_pdf_end_to_end_cleanup(client, mock_embedding, monkeypatch, tmp_path):
    mock_add = AsyncMock()
    monkeypatch.setattr("app.repositories.vector_repository.VectorRepository.add", mock_add)

    # Mock PDFParser to return OCR-extracted pages
    mock_ocr_page = ParsedPage(
        page_number=1,
        text="## Question 1\nWhat is the difference between TCP and UDP?",
        is_ocr=True,
    )

    with patch("app.services.document_service.get_parser") as mock_get_parser:
        mock_parser_instance = MagicMock()
        mock_parser_instance.parse_file.return_value = [mock_ocr_page]
        mock_get_parser.return_value = mock_parser_instance

        files = {"file": ("scanned_exam.pdf", io.BytesIO(b"%PDF-1.4 dummy pdf"), "application/pdf")}
        upload_res = client.post("/doc/upload", files=files)

        assert upload_res.status_code == 200
        data = upload_res.json()["data"]
        assert data["filename"] == "scanned_exam.pdf"
        assert data["chunks"] >= 1
        doc_id = data["document_id"]

        # Ensure temporary file is cleaned up
        temp_dir = Path(tempfile.gettempdir())
        dangling_files = list(temp_dir.glob(f"manan_upload_{doc_id}*"))
        assert len(dangling_files) == 0


def test_document_ingest_ocr_failure_cleans_temp_file_and_rolls_back(client, monkeypatch):
    mock_delete_cloudinary = MagicMock()
    monkeypatch.setattr(
        "app.integrations.storage.cloudinary_storage.CloudinaryStorage.delete_file",
        mock_delete_cloudinary,
    )

    with patch("app.services.document_service.get_parser") as mock_get_parser:
        mock_parser_instance = MagicMock()
        mock_parser_instance.parse_file.side_effect = DocumentProcessingError("HF OCR API failed to parse scanned pages")
        mock_get_parser.return_value = mock_parser_instance

        files = {"file": ("corrupt_scanned.pdf", io.BytesIO(b"%PDF-1.4 corrupt"), "application/pdf")}
        upload_res = client.post("/doc/upload", files=files)

        assert upload_res.status_code == 422
        # Verify Cloudinary rollback was called
        mock_delete_cloudinary.assert_called_once()
