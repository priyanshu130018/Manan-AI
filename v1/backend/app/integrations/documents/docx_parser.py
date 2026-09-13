import docx
from app.integrations.documents.base import ParsedPage


class DocxParser:
    def parse_file(self, file_path: str) -> list[ParsedPage]:
        doc = docx.Document(file_path)
        pages: list[ParsedPage] = []
        cur_text = []
        page_num = 1
        cur_heading = None

        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue
            if p.style and p.style.name and p.style.name.startswith("Heading"):
                cur_heading = text
            cur_text.append(text)

            # Approximate logical page breaks every ~450 words
            if len(" ".join(cur_text).split()) >= 450:
                pages.append(ParsedPage(
                    page_number=page_num,
                    text="\n\n".join(cur_text),
                    heading=cur_heading,
                ))
                page_num += 1
                cur_text = []

        if cur_text:
            pages.append(ParsedPage(
                page_number=page_num,
                text="\n\n".join(cur_text),
                heading=cur_heading,
            ))
        return pages
