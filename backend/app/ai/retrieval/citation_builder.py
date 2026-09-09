from app.schemas.chat import Citation
from app.schemas.retrieval import RetrievedChunk


class CitationBuilder:
    def build(
        self,
        chunks: list[RetrievedChunk],
    ) -> list[Citation]:
        citations: list[Citation] = []

        seen: set[tuple[str, int]] = set()

        for chunk in chunks:
            filename = chunk.metadata.get(
                "filename",
                "Unknown",
            )

            chunk_index = chunk.metadata.get(
                "chunk",
                0,
            )

            key = (
                filename,
                chunk_index,
            )

            if key in seen:
                continue

            seen.add(key)

            citations.append(
                Citation(
                    filename=filename,
                    chunk=chunk_index,
                )
            )

        return citations