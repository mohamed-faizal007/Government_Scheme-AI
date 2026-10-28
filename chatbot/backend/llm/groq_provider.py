import logging

from groq import APIConnectionError, APIStatusError, Groq

from ..config import settings
from . import limits
from .base import BaseLLM, ContextTooLargeError, ProviderUnavailable

logger = logging.getLogger(__name__)

TIMEOUT_S = 20


class GroqProvider(BaseLLM):
    """Groq-backed LLM: GROQ_MODEL, then GROQ_FALLBACK_MODEL (each has its own quota).

    A 429 moves straight to the next model with no waiting. A model whose daily limit is used up is
    skipped until its reset time. When no model answers it raises ProviderUnavailable so the
    FallbackChain can try the next provider.
    """

    def __init__(self, model: str | None = None, fallback_model: str | None = None):
        self.model = model or settings.groq_model
        self.fallback_model = fallback_model or settings.groq_fallback_model
        # max_retries=0: the SDK's own 429 retry sleeps 30s+ before we ever see the error.
        self.client = Groq(api_key=settings.groq_api_key, max_retries=0, timeout=TIMEOUT_S) if settings.groq_api_key else None

    def _models(self) -> list[str]:
        models = [self.model]
        if self.fallback_model and self.fallback_model != self.model:
            models.append(self.fallback_model)
        return [m for m in models if m]

    def generate(self, prompt: str, system: str = "") -> str:
        if self.client is None:
            raise ProviderUnavailable("groq: no API key")
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        for model in self._models():
            key = f"groq:{model}"
            if limits.is_blocked(key):
                logger.info("llm_provider=groq model=%s skipped (daily limit)", model)
                continue
            try:
                completion = self.client.chat.completions.create(model=model, messages=messages)
            except APIStatusError as exc:
                text = str(exc)
                # Groq reports an oversized prompt as 413, and sometimes as a 429 whose message says
                # "Request too large"; switching model cannot fix either.
                if exc.status_code == 413 or "request too large" in text.lower():
                    logger.warning("llm_provider=groq model=%s context_too_large", model)
                    raise ContextTooLargeError(text) from exc
                if exc.status_code == 429:
                    if limits.is_daily_limit(text):
                        limits.block(key, limits.groq_reset_seconds(text))
                    else:
                        logger.warning("llm_provider=groq model=%s rate_limited, trying the next model", model)
                    continue
                logger.warning("llm_provider=groq model=%s status_error=%s, trying the next model", model, exc.status_code)
                continue
            except APIConnectionError:
                logger.warning("llm_provider=groq model=%s network_failure, trying the next model", model)
                continue
            content = completion.choices[0].message.content
            if not content:
                logger.warning("llm_provider=groq model=%s invalid_response", model)
                continue
            usage = getattr(completion, "usage", None)
            logger.info("llm_provider=groq model=%s prompt_tokens=%s", model, getattr(usage, "prompt_tokens", "?"))
            return content
        raise ProviderUnavailable("groq: no model answered")
