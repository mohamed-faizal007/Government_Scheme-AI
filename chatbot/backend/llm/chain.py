import logging

from .base import BaseLLM, ProviderUnavailable

logger = logging.getLogger(__name__)


class FallbackChain(BaseLLM):
    """Tries each provider in order and returns the first answer.

    A provider raises ProviderUnavailable when it cannot answer; the chain moves straight on with no
    waiting. ContextTooLargeError is not caught: the caller retries with fewer schemes. `last_provider`
    names the provider that answered the latest call (for logs only).
    """

    def __init__(self, providers: list[BaseLLM]):
        self.providers = providers
        self.last_provider = ""

    def generate(self, prompt: str, system: str = "") -> str:
        self.last_provider = ""
        for provider in self.providers:
            try:
                text = provider.generate(prompt, system)
            except ProviderUnavailable as exc:
                logger.warning("llm_chain: %s unavailable (%s), trying the next provider", type(provider).__name__, exc)
                continue
            self.last_provider = getattr(provider, "name", type(provider).__name__)
            return text
        raise ProviderUnavailable("every provider failed")
