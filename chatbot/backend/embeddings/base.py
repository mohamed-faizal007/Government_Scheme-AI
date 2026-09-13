from abc import ABC, abstractmethod


class BaseEmbedder(ABC):
    """Abstraction over an embedding model so retrieval code never depends on a specific one."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError
