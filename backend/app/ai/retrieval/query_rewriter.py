from app.ai.llm.factory import LLMFactory


class QueryRewriter:
    def __init__(
        self,
    ) -> None:
        self._llm = LLMFactory.get_llm()

    async def rewrite(
        self,
        question: str,
    ) -> str:
        prompt = f"""
Rewrite the following user question into a concise semantic search query.

Rules:
- Preserve the original meaning.
- Remove unnecessary words.
- Return only the rewritten query.

Question:
{question}
"""

        response = await self._llm.generate(
            prompt,
        )

        return response.strip()