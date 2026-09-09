import re


class TextSplitter:
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> None:
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def split(
        self,
        text: str,
    ) -> list[str]:
        paragraphs = [
            paragraph.strip()
            for paragraph in text.split("\n")
            if paragraph.strip()
        ]

        chunks: list[str] = []

        current_chunk = ""

        for paragraph in paragraphs:
            if (
                len(current_chunk)
                + len(paragraph)
                + 1
                <= self._chunk_size
            ):
                if current_chunk:
                    current_chunk += "\n"

                current_chunk += paragraph
                continue

            if current_chunk:
                chunks.append(current_chunk)

            if len(paragraph) <= self._chunk_size:
                current_chunk = paragraph
                continue

            sentences = re.split(
                r"(?<=[.!?])\s+",
                paragraph,
            )

            current_chunk = ""

            for sentence in sentences:
                if (
                    len(current_chunk)
                    + len(sentence)
                    + 1
                    <= self._chunk_size
                ):
                    if current_chunk:
                        current_chunk += " "

                    current_chunk += sentence
                else:
                    if current_chunk:
                        chunks.append(current_chunk)

                    overlap = (
                        current_chunk[
                            -self._chunk_overlap :
                        ]
                        if current_chunk
                        else ""
                    )

                    current_chunk = (
                        overlap + sentence
                    )

        if current_chunk:
            chunks.append(current_chunk)

        return chunks