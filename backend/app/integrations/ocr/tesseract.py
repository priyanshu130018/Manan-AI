import shutil
from dataclasses import dataclass
from PIL import Image
import pytesseract

from app.core.config import get_settings
from app.core.logging import LoggerFactory

logger = LoggerFactory.create_logger("TesseractOCR")


@dataclass
class OCRResult:
    text: str
    page_number: int = 1
    confidence: float = 0.0


class TesseractOCR:
    def __init__(self) -> None:
        settings = get_settings()
        if settings.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
        self._available = self._check_availability()

    def _check_availability(self) -> bool:
        try:
            cmd = pytesseract.pytesseract.tesseract_cmd or "tesseract"
            return shutil.which(cmd) is not None or pytesseract.get_tesseract_version() is not None
        except Exception:
            return False

    @property
    def is_available(self) -> bool:
        return self._available

    def extract_text(self, image: Image.Image, page_number: int = 1) -> OCRResult:
        if not self._available:
            logger.warning("Tesseract OCR binary is not found on host system.")
            return OCRResult(text="", page_number=page_number, confidence=0.0)
        try:
            text = pytesseract.image_to_string(image)
            clean_text = text.strip()
            return OCRResult(
                text=clean_text,
                page_number=page_number,
                confidence=0.85 if clean_text else 0.0,
            )
        except Exception as e:
            logger.warning("OCR extraction failed on page %d: %s", page_number, str(e))
            return OCRResult(text="", page_number=page_number, confidence=0.0)


# Alias for backward compatibility
TesseractOCRService = TesseractOCR
