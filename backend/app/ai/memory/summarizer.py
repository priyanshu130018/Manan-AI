from app.ai.llm.factory import LLMFactory


class ConversationSummarizer:
    def __init__(
        self,
    ) -> None:
        self._llm = LLMFactory.get_llm()

    async def summarize(
        self,
        history: list[dict[str, str]],
    ) -> str:
        if not history:
            return ""

        conversation = "\n".join(
            f"{message['role'].capitalize()}: {message['content']}"
            for message in history
        )

        prompt = f"""
Summarize the following conversation.

Rules:
- Preserve important facts.
- Preserve user preferences.
- Preserve unresolved questions.
- Keep the summary under 200 words.

Conversation:

{conversation}
"""

        return (
            await self._llm.generate(
                prompt,
            )
        ).strip()