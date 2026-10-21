import logging
import time

from groq import APIConnectionError, APIStatusError, Groq

from ..config import settings
from .base import BaseLLM, ContextTooLargeError
from .ollama_provider import OllamaProvider

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


class GroqProvider(BaseLLM):
    """Groq-backed LLM. On a 429 it switches immediately to the fallback model (which has
    its own token bucket), then retries both with backoff, and only then falls back to
    Ollama. Other failures fall back to Ollama directly."""

    def __init__(self, model: str | None = None, fallback: BaseLLM | None = None, fallback_model: str | None = None):
        self.model = model or settings.groq_model
        self.fallback_model = fallback_model or settings.groq_fallback_model
        # max_retries=0: the SDK's own 429 retry sleeps 30s+ before we ever see the error,
        # which defeats switching to the fallback model.
        self.client = Groq(api_key=settings.groq_api_key, max_retries=0)
        self.fallback = fallback or OllamaProvider()

    def _models(self) -> list[str]:
        models = [self.model]
        if self.fallback_model and self.fallback_model != self.model:
            models.append(self.fallback_model)
        return models

    def generate(self, prompt: str, system: str = "") -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        models = self._models()
        # Rounds: each round tries every model once; backoff only happens between rounds.
        for round_no in range(1, MAX_RETRIES + 1):
            rate_limited_all = True
            for model in models:
                try:
                    completion = self.client.chat.completions.create(model=model, messages=messages)
                    content = completion.choices[0].message.content
                    if not content:
                        logger.warning("llm_provider=groq model=%s invalid_response, falling back to ollama", model)
                        return self._fallback(prompt, system)
                    usage = getattr(completion, "usage", None)
                    logger.info("llm_provider=groq model=%s prompt_tokens=%s", model, getattr(usage, "prompt_tokens", "?"))
                    return content
                except APIStatusError as exc:
                    # Groq reports an oversized prompt as 413, and sometimes as a 429 whose
                    # message says "Request too large"; switching model or waiting cannot fix either.
                    if exc.status_code == 413 or "request too large" in str(exc).lower():
                        logger.warning("llm_provider=groq model=%s context_too_large", model)
                        raise ContextTooLargeError(str(exc)) from exc
                    if exc.status_code == 429:
                        logger.warning("llm_provider=groq model=%s rate_limited round=%d", model, round_no)
                        continue
                    rate_limited_all = False
                    if exc.status_code == 503 and round_no == 1:
                        logger.warning("llm_provider=groq model=%s temporary_failure retrying_once", model)
                        break
                    logger.warning("llm_provider=groq model=%s status_error=%s falling back to ollama", model, exc.status_code)
                    return self._fallback(prompt, system)
                except APIConnectionError:
                    logger.warning("llm_provider=groq network_failure falling back to ollama")
                    return self._fallback(prompt, system)
            if rate_limited_all and round_no < MAX_RETRIES:
                wait = 2 ** round_no
                logger.warning("llm_provider=groq all_models_rate_limited retry_in=%ss round=%d", wait, round_no)
                time.sleep(wait)

        logger.warning("llm_provider=groq rate_limit_exhausted falling back to ollama")
        return self._fallback(prompt, system)

    def _fallback(self, prompt: str, system: str) -> str:
        return self.fallback.generate(prompt, system)
