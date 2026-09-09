from pathlib import Path

from pypdf import PdfReader


class PDFLoader:
    def load(
        self,
        file_path: str,
    ) -> str:
        reader = PdfReader(
            Path(file_path),
        )

        pages: list[str] = []

        for page in reader.pages:
            pages.append(
                page.extract_text() or ""
            )

        return "\n".join(
            pages,
        )