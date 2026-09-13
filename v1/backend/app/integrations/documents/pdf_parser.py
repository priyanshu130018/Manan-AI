import io
from pathlib import Path
from pypdf import PdfReader
from PIL import Image

from app.core.logging import LoggerFactory
from app.integrations.documents.base import ParsedPage
from app.integrations.ocr.tesseract import TesseractOCR

logger = LoggerFactory.create_logger("PDFParser")


class PDFParser:
    def __init__(self, ocr: TesseractOCR | None = None) -> None:
        self._ocr = ocr or TesseractOCR()

    def parse_file(self, file_path: str) -> list[ParsedPage]:
        reader = PdfReader(Path(file_path))
        pages: list[ParsedPage] = []
        needs_ocr_pages: list[tuple[int, any]] = []

        for idx, page in enumerate(reader.pages, start=1):
            try:
                extracted = page.extract_text() or ""
            except Exception:
                extracted = ""

            cleaned = extracted.strip()
            # If extracted text is substantial (> 40 chars), treat as text page
            if len(cleaned) >= 40:
                pages.append(ParsedPage(
                    page_number=idx,
                    text=cleaned,
                    is_ocr=False,
                ))
            else:
                needs_ocr_pages.append((idx, page))

        # If pages have insufficient text, inspect via OCR
        if needs_ocr_pages:
            logger.info("%d pages in %s need OCR inspection.", len(needs_ocr_pages), file_path)
            ocr_succeeded = False
            try:
                from pdf2image import convert_from_path
                images = convert_from_path(file_path)
                for idx, page in needs_ocr_pages:
                    if idx - 1 < len(images):
                        img = images[idx - 1]
                        ocr_res = self._ocr.extract_text(img, page_number=idx)
                        if ocr_res.text:
                            pages.append(ParsedPage(
                                page_number=idx,
                                text=ocr_res.text,
                                is_ocr=True,
                            ))
                            ocr_succeeded = True
            except Exception as e:
                logger.warning("pdf2image/OCR failed for %s: %s", file_path, str(e))

            # Fallback: check embedded images inside the page if pdf2image was unavailable
            if not ocr_succeeded:
                for idx, page in needs_ocr_pages:
                    embedded_text = []
                    try:
                        for img_obj in page.images:
                            pil_img = Image.open(io.BytesIO(img_obj.data))
                            res = self._ocr.extract_text(pil_img, page_number=idx)
                            if res.text:
                                embedded_text.append(res.text)
                    except Exception:
                        pass
                    if embedded_text:
                        pages.append(ParsedPage(
                            page_number=idx,
                            text="\n\n".join(embedded_text),
                            is_ocr=True,
                        ))

        pages.sort(key=lambda p: p.page_number)
        return pages
