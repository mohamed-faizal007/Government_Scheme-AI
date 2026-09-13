import logging
import time

from groq import APIConnectionError, APIStatusError, Groq

from ..config import settings
from .base import BaseLLM
from .ollama_provider import OllamaProvider

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


class GroqProvider(BaseLLM):
    """Groq-backed LLM. Falls back to Ollama on invalid responses or network failure —
    never on rate limits, which are retried against Groq itself first."""

    def __init__(self, model: str | None = None, fallback: BaseLLM | None = None):
        self.model = model or settings.groq_model
        self.client = Groq(api_key=settings.groq_api_key)
        self.fallback = fallback or OllamaProvider()

    def generate(self, prompt: str, system: str = "") -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        attempt = 0
        while attempt < MAX_RETRIES:
            attempt += 1
            try:
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                )
                content = completion.choices[0].message.content
                if not content:
                    logger.warning("llm_provider=groq invalid_response, falling back to ollama")
                    return self._fallback(prompt, system)
                logger.info("llm_provider=groq model=%s", self.model)
                return content
            except APIStatusError as exc:
                if exc.status_code == 429:
                    wait = 2 ** attempt
                    logger.warning("llm_provider=groq rate_limited retry_in=%ss attempt=%d", wait, attempt)
                    time.sleep(wait)
                    continue
                if exc.status_code == 503:
                    logger.warning("llm_provider=groq temporary_failure retrying_once")
                    if attempt == 1:
                        continue
                    return self._fallback(prompt, system)
                logger.warning("llm_provider=groq status_error=%s falling back to ollama", exc.status_code)
                return self._fallback(prompt, system)
            except APIConnectionError:
                logger.warning("llm_provider=groq network_failure falling back to ollama")
                return self._fallback(prompt, system)

        logger.warning("llm_provider=groq rate_limit_exhausted falling back to ollama")
        return self._fallback(prompt, system)

    def _fallback(self, prompt: str, system: str) -> str:
        return self.fallback.generate(prompt, system)
