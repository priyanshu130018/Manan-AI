import time
import uuid
from langchain_core.messages import HumanMessage
from app.models.entities.message import MessageEntity
from app.repositories.session_repository import SessionRepository
from app.repositories.memory_repository import MemoryRepository
from app.integrations.llm.factory import get_llm
from app.core.logging import LoggerFactory

logger = LoggerFactory.create_logger("MemoryService")


class MemoryService:
    def __init__(
        self,
        session_repo: SessionRepository | None = None,
        memory_repo: MemoryRepository | None = None,
        llm=None,
    ) -> None:
        self._repo = session_repo or SessionRepository()
        self._memory_repo = memory_repo or MemoryRepository()
        self._llm = llm

    def _get_llm(self):
        if self._llm is None:
            self._llm = get_llm()
        return self._llm

    # ---------------------------------------------------------
    # Short-Term Session Memory (Messages & Per-Session Summary)
    # ---------------------------------------------------------

    async def add_user_message(self, session_id: str, content: str, user_id: str | None = None) -> MessageEntity:
        msg = MessageEntity(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role="user",
            content=content,
            citations=[],
            created_at=time.time(),
        )
        if not session_id.startswith("temp-"):
            await self._repo.get_or_create_session(session_id, user_id=user_id)
            await self._repo.add_message(msg)
        return msg

    async def add_assistant_message(
        self,
        session_id: str,
        content: str,
        citations: list[dict] | None = None,
        user_id: str | None = None,
    ) -> MessageEntity:
        msg = MessageEntity(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role="assistant",
            content=content,
            citations=citations or [],
            created_at=time.time(),
        )
        if not session_id.startswith("temp-"):
            await self._repo.get_or_create_session(session_id, user_id=user_id)
            await self._repo.add_message(msg)
        return msg

    async def get_history(self, session_id: str) -> list[MessageEntity]:
        if session_id.startswith("temp-"):
            return []
        return await self._repo.get_messages(session_id)

    async def get_summary(self, session_id: str) -> str:
        if session_id.startswith("temp-"):
            return ""
        return await self._repo.get_summary(session_id)

    async def save_summary(self, session_id: str, summary: str) -> None:
        if session_id.startswith("temp-"):
            return
        await self._repo.save_summary(session_id, summary)

    async def trim_history(self, session_id: str, keep_last: int = 10) -> None:
        if session_id.startswith("temp-"):
            return
        await self._repo.trim_messages(session_id, keep_last=keep_last)

    async def summarize_history(self, messages: list[MessageEntity]) -> str:
        if not messages:
            return ""
        convo_lines = [f"{m.role.capitalize()}: {m.content}" for m in messages]
        convo_text = "\n".join(convo_lines)
        prompt = f"""Summarize the key information, discussed topics, and study concepts from this conversation into a concise bullet-point summary (under 150 words):

{convo_text}

Summary:"""
        try:
            res = await self._get_llm().ainvoke([HumanMessage(content=prompt)])
            return getattr(res, "content", str(res))
        except Exception as e:
            logger.warning("Conversation summarization skipped on error: %s", str(e))
            return ""

    # ---------------------------------------------------------
    # Long-Term Cross-Chat Memory (Persisted in PostgreSQL `memories`)
    # ---------------------------------------------------------

    async def get_long_term_memories(self, user_id: str | None = None, limit: int = 20) -> list[dict]:
        return await self._memory_repo.list_memories(user_id=user_id, limit=limit)

    async def save_long_term_memory(
        self,
        content: str,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> dict:
        return await self._memory_repo.create_memory(
            content=content,
            user_id=user_id,
            source_session_id=session_id,
        )

    async def update_long_term_memory(
        self,
        memory_id: str,
        content: str,
        user_id: str | None = None,
    ) -> dict | None:
        return await self._memory_repo.update_memory(
            memory_id=memory_id,
            content=content,
            user_id=user_id,
        )

    async def delete_long_term_memory(self, memory_id: str, user_id: str | None = None) -> bool:
        return await self._memory_repo.delete_memory(memory_id, user_id=user_id)

    async def clear_long_term_memories(self, user_id: str | None = None) -> int:
        return await self._memory_repo.clear_all_memories(user_id=user_id)

    async def extract_and_save_facts(self, session_id: str, user_message: str, user_id: str | None = None) -> None:
        """Extract explicit user facts / learning preferences from message and store in long-term memory."""
        if session_id.startswith("temp-") or len(user_message.strip()) < 5:
            return

        prompt = f"""You are a memory extractor. Analyze the user statement below.
If the user states an explicit personal fact, goal, background, or preference (e.g. "I am preparing for MCAT", "Call me Alex", "I prefer Python over C++", "I struggle with organic chemistry"), extract it into 1-2 concise declarative sentences.
If the user is just asking a question, greeting, or has no explicit personal fact/preference, respond with "NONE".

User message: "{user_message}"

Extracted Fact:"""
        try:
            res = await self._get_llm().ainvoke([HumanMessage(content=prompt)])
            result = str(getattr(res, "content", res)).strip()
            if result and result.upper() != "NONE" and not result.upper().startswith("NONE"):
                # Clean up any quotes or prefixes
                clean_fact = result.strip('"').strip("'").strip()
                if clean_fact and len(clean_fact) > 3:
                    await self.save_long_term_memory(content=clean_fact, user_id=user_id, session_id=session_id)
                    logger.info("Saved new long-term memory from session %s (user %s): %s", session_id, user_id, clean_fact)
        except Exception as e:
            logger.debug("Fact extraction skipped on error: %s", str(e))


# Backward compatibility aliases
ConversationMemoryService = MemoryService
ConversationSummarizer = MemoryService
