from abc import ABC, abstractmethod


class ContextTooLargeError(Exception):
    """Raised when the provider rejects a request because the prompt is too large
    (e.g. HTTP 413), so the caller can retry with a smaller context before
    falling back to another provider."""


class BaseLLM(ABC):
    """Abstraction over an LLM provider so callers never depend on a specific vendor SDK."""

    @abstractmethod
    def generate(self, prompt: str, system: str = "") -> str:
        """Return the model's text response for `prompt` under the given `system` instruction."""
        raise NotImplementedError
