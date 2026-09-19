from PIL import Image
from app.integrations.documents.base import ParsedPage
from app.integrations.ocr import HuggingFaceOCRService, OCRService


class ImageParser:
    def __init__(self, ocr: OCRService | None = None) -> None:
        self._ocr = ocr or HuggingFaceOCRService()

    def parse_file(self, file_path: str) -> list[ParsedPage]:
        img = Image.open(file_path)
        res = self._ocr.extract_text(img, page_number=1)
        if res.text and res.text.strip():
            return [ParsedPage(page_number=1, text=res.text.strip(), is_ocr=True)]
        return []
