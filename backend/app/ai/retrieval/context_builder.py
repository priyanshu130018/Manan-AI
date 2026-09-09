from app.schemas.retrieval import RetrievedChunk


class ContextBuilder:
    def build(
        self,
        chunks: list[RetrievedChunk],
    ) -> str:
        return "\n\n".join(
            chunk.document
            for chunk in chunks
        )