from abc import ABC, abstractmethod


class BaseLLM(ABC):
    """Abstraction over an LLM provider so callers never depend on a specific vendor SDK."""

    @abstractmethod
    def generate(self, prompt: str, system: str = "") -> str:
        """Return the model's text response for `prompt` under the given `system` instruction."""
        raise NotImplementedError
