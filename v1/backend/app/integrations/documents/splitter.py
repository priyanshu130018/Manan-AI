import re
import uuid
from app.models.entities.chunk import DocumentChunk
from app.integrations.documents.base import ParsedPage


class StructurePreservingSplitter:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200) -> None:
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def split_document(
        self,
        document_id: str,
        filename: str,
        source_type: str,
        pages: list[ParsedPage],
    ) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        global_index = 1

        for page in pages:
            raw_text = page.text.strip()
            if not raw_text:
                continue

            # Split text by paragraphs first, preserving natural structural boundaries
            paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
            if not paragraphs:
                paragraphs = [p.strip() for p in raw_text.split("\n") if p.strip()]

            cur_chunk = ""
            for paragraph in paragraphs:
                if len(cur_chunk) + len(paragraph) + 2 <= self._chunk_size:
                    cur_chunk += ("\n\n" if cur_chunk else "") + paragraph
                    continue

                if cur_chunk:
                    chunks.append(DocumentChunk(
                        chunk_id=str(uuid.uuid4()),
                        document_id=document_id,
                        filename=filename,
                        page_number=page.page_number,
                        chunk_index=global_index,
                        text=cur_chunk.strip(),
                        source_type=source_type,
                        heading=page.heading,
                    ))
                    global_index += 1
                    overlap = cur_chunk[-self._chunk_overlap:] if self._chunk_overlap > 0 else ""
                    cur_chunk = overlap.strip()

                if len(paragraph) <= self._chunk_size:
                    if cur_chunk:
                        if len(cur_chunk) + len(paragraph) + 2 <= self._chunk_size:
                            cur_chunk += ("\n\n" if cur_chunk else "") + paragraph
                        else:
                            chunks.append(DocumentChunk(
                                chunk_id=str(uuid.uuid4()),
                                document_id=document_id,
                                filename=filename,
                                page_number=page.page_number,
                                chunk_index=global_index,
                                text=cur_chunk.strip(),
                                source_type=source_type,
                                heading=page.heading,
                            ))
                            global_index += 1
                            cur_chunk = paragraph
                    else:
                        cur_chunk = paragraph
                    continue

                # Paragraph exceeds chunk_size, split by sentences
                sentences = re.split(r"(?<=[.!?])\s+", paragraph)
                for sentence in sentences:
                    if not sentence.strip():
                        continue
                    if len(cur_chunk) + len(sentence) + 1 <= self._chunk_size:
                        cur_chunk += (" " if cur_chunk else "") + sentence
                    else:
                        if cur_chunk:
                            chunks.append(DocumentChunk(
                                chunk_id=str(uuid.uuid4()),
                                document_id=document_id,
                                filename=filename,
                                page_number=page.page_number,
                                chunk_index=global_index,
                                text=cur_chunk.strip(),
                                source_type=source_type,
                                heading=page.heading,
                            ))
                            global_index += 1
                            overlap = cur_chunk[-self._chunk_overlap:] if self._chunk_overlap > 0 else ""
                            cur_chunk = (overlap + " " + sentence).strip()
                        else:
                            for i in range(0, len(sentence), self._chunk_size - self._chunk_overlap):
                                sub = sentence[i:i + self._chunk_size].strip()
                                if sub:
                                    chunks.append(DocumentChunk(
                                        chunk_id=str(uuid.uuid4()),
                                        document_id=document_id,
                                        filename=filename,
                                        page_number=page.page_number,
                                        chunk_index=global_index,
                                        text=sub,
                                        source_type=source_type,
                                        heading=page.heading,
                                    ))
                                    global_index += 1
                            cur_chunk = ""

            if cur_chunk and cur_chunk.strip():
                chunks.append(DocumentChunk(
                    chunk_id=str(uuid.uuid4()),
                    document_id=document_id,
                    filename=filename,
                    page_number=page.page_number,
                    chunk_index=global_index,
                    text=cur_chunk.strip(),
                    source_type=source_type,
                    heading=page.heading,
                ))
                global_index += 1

        return chunks
