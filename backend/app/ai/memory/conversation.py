from collections import defaultdict

from app.ai.memory.base import BaseMemory


class ConversationMemory(BaseMemory):
    def __init__(
        self,
    ) -> None:
        self._history = defaultdict(list)

        self._summary: dict[str, str] = {}

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> None:
        self._history[session_id].append(
            {
                "role": role,
                "content": content,
            }
        )

    async def get_history(
        self,
        session_id: str,
    ) -> list[dict[str, str]]:
        return self._history.get(
            session_id,
            [],
        )

    async def clear(
        self,
        session_id: str,
    ) -> None:
        self._history.pop(
            session_id,
            None,
        )

        self._summary.pop(
            session_id,
            None,
        )

    async def get_summary(
        self,
        session_id: str,
    ) -> str:
        return self._summary.get(
            session_id,
            "",
        )

    async def save_summary(
        self,
        session_id: str,
        summary: str,
    ) -> None:
        self._summary[session_id] = summary

    async def trim_history(
        self,
        session_id: str,
        keep_last: int,
    ) -> None:
        history = self._history.get(
            session_id,
            [],
        )

        self._history[session_id] = (
            history[-keep_last:]
        )