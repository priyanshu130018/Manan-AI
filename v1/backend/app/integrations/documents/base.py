from dataclasses import dataclass


@dataclass
class ParsedPage:
    page_number: int
    text: str
    heading: str | None = None
    is_ocr: bool = False
