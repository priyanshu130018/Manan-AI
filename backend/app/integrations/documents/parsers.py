from pathlib import Path
from typing import Protocol

from app.core.exceptions import DocumentValidationError
from app.models.entities.enums import SourceType
from app.integrations.documents.base import ParsedPage
from app.integrations.documents.pdf_parser import PDFParser
from app.integrations.documents.docx_parser import DocxParser
from app.integrations.documents.pptx_parser import PptxParser
from app.integrations.documents.txt_parser import TxtParser
from app.integrations.documents.image_parser import ImageParser


class DocumentParser(Protocol):
    def parse_file(self, file_path: str) -> list[ParsedPage]:
        ...


def detect_source_type(filename: str) -> SourceType:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return SourceType.PDF
    elif ext in [".docx", ".doc"]:
        return SourceType.DOCX
    elif ext in [".pptx", ".ppt"]:
        return SourceType.PPTX
    elif ext in [".txt", ".md", ".csv", ".json", ".sql", ".log"]:
        return SourceType.TXT
    elif ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"]:
        return SourceType.IMAGE
    else:
        raise DocumentValidationError(f"Unsupported file format: {ext}")


def get_parser(source_type: SourceType | str) -> DocumentParser:
    st = SourceType(source_type) if isinstance(source_type, str) else source_type
    if st in [SourceType.PDF, SourceType.SCANNED_PDF]:
        return PDFParser()
    elif st == SourceType.DOCX:
        return DocxParser()
    elif st == SourceType.PPTX:
        return PptxParser()
    elif st == SourceType.TXT:
        return TxtParser()
    elif st == SourceType.IMAGE:
        return ImageParser()
    raise DocumentValidationError(f"No parser available for source type {st}")
