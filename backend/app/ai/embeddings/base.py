from abc import ABC
from abc import abstractmethod


class BaseEmbedding(ABC):
    @abstractmethod
    async def embed(
        self,
        text: str,
    ) -> list[float]:
        raise NotImplementedError