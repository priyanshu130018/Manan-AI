from abc import ABC
from abc import abstractmethod


class BaseLLM(ABC):
    @abstractmethod
    async def generate(
        self,
        prompt: str,
    ) -> str:
        raise NotImplementedError