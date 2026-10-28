import logging

from .base import BaseLLM, ProviderUnavailable

logger = logging.getLogger(__name__)


class FallbackChain(BaseLLM):
    """Tries each provider in order and returns the first answer.

    A provider raises ProviderUnavailable when it cannot answer; the chain moves straight on with no
    waiting. ContextTooLargeError is not caught: the caller retries with fewer schemes.
    """

    def __init__(self, providers: list[BaseLLM]):
        self.providers = providers

    def generate(self, prompt: str, system: str = "") -> str:
        for provider in self.providers:
            try:
                return provider.generate(prompt, system)
            except ProviderUnavailable as exc:
                logger.warning("llm_chain: %s unavailable (%s), trying the next provider", type(provider).__name__, exc)
        raise ProviderUnavailable("every provider failed")
