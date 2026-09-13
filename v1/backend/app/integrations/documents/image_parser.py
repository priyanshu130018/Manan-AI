from PIL import Image
from app.integrations.documents.base import ParsedPage
from app.integrations.ocr.tesseract import TesseractOCR


class ImageParser:
    def __init__(self, ocr: TesseractOCR | None = None) -> None:
        self._ocr = ocr or TesseractOCR()

    def parse_file(self, file_path: str) -> list[ParsedPage]:
        img = Image.open(file_path)
        res = self._ocr.extract_text(img, page_number=1)
        if res.text:
            return [ParsedPage(page_number=1, text=res.text, is_ocr=True)]
        return []
