from pathlib import Path
from app.integrations.documents.base import ParsedPage


class TxtParser:
    def parse_file(self, file_path: str) -> list[ParsedPage]:
        p = Path(file_path)
        content = p.read_text(encoding="utf-8", errors="replace")
        if not content.strip():
            return []

        # Split into logical pages (~3000 chars per page if long)
        page_size = 3000
        pages: list[ParsedPage] = []
        if len(content) <= page_size:
            pages.append(ParsedPage(page_number=1, text=content.strip()))
        else:
            paragraphs = content.split("\n\n")
            cur_page_text = ""
            page_num = 1
            for para in paragraphs:
                if len(cur_page_text) + len(para) > page_size and cur_page_text:
                    pages.append(ParsedPage(page_number=page_num, text=cur_page_text.strip()))
                    page_num += 1
                    cur_page_text = para
                else:
                    cur_page_text += ("\n\n" if cur_page_text else "") + para
            if cur_page_text.strip():
                pages.append(ParsedPage(page_number=page_num, text=cur_page_text.strip()))
        return pages
