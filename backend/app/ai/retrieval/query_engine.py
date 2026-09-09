from app.ai.retrieval.retriever import Retriever


class QueryEngine:
    def __init__(self) -> None:
        self._retriever = Retriever()

    async def query(
        self,
        question: str,
    ) -> str:
        chunks = await self._retriever.retrieve(
            question,
        )

        return "\n\n".join(chunks)