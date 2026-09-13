from app.domain.entities.message import MessageEntity
from app.infrastructure.ai.llm.gemini import GeminiLLM

class ConversationSummarizer:
    def __init__(self, llm: GeminiLLM | None = None) -> None:
        self._llm = llm or GeminiLLM()

    async def summarize(self, messages: list[MessageEntity]) -> str:
        if not messages:
            return ""
        convo_lines = [f"{m.role.capitalize()}: {m.content}" for m in messages]
        convo_text = "\n".join(convo_lines)
        prompt = f"""Summarize the key information, discussed topics, and study concepts from this conversation into a concise bullet-point summary (under 150 words):

{convo_text}

Summary:"""
        try:
            return await self._llm.generate(prompt)
        except Exception:
            return ""
