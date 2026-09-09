from abc import ABC
from abc import abstractmethod


class BaseMemory(ABC):
    @abstractmethod
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_history(
        self,
        session_id: str,
    ) -> list[dict[str, str]]:
        raise NotImplementedError

    @abstractmethod
    async def clear(
        self,
        session_id: str,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_summary(
        self,
        session_id: str,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    async def save_summary(
        self,
        session_id: str,
        summary: str,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def trim_history(
        self,
        session_id: str,
        keep_last: int,
    ) -> None:
        raise NotImplementedError