import logging

from ..config import settings
from ..nlu import llm_understander as nlu
from . import limits
from .base import BaseLLM, ProviderUnavailable

logger = logging.getLogger(__name__)


class GeminiProvider(BaseLLM):
    """Gemini generation fallback: GEMINI_MODEL, then GEMINI_MODEL_FALLBACK.

    Only the system prompt and the prompt (question + retrieved scheme text) are sent. It shares the
    daily cap, circuit breaker and client of the NLU layer, so one key budget covers both. A 429/5xx
    moves straight to the next model with no waiting; a model whose daily quota is used up is skipped
    until the reset. When nothing answers it raises ProviderUnavailable for the FallbackChain.
    """

    @staticmethod
    def _models() -> list[str]:
        names = [settings.gemini_model, settings.gemini_model_fallback]
        return list(dict.fromkeys(n for n in names if n))

    def generate(self, prompt: str, system: str = "") -> str:
        models = self._models()
        if not settings.gemini_api_key or not models:
            raise ProviderUnavailable("gemini: not configured")
        if nlu._breaker_open():
            raise ProviderUnavailable("gemini: circuit breaker open")

        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system or None,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            thinking_config=types.ThinkingConfig(thinking_level="MINIMAL"),
        )
        transient = False
        for model in models:
            key = f"gemini:{model}"
            if limits.is_blocked(key):
                logger.info("llm_provider=gemini model=%s skipped (daily limit)", model)
                continue
            if not nlu.reserve_daily():
                logger.warning("llm_provider=gemini daily_cap_reached")
                break
            try:
                response = nlu._get_client().models.generate_content(model=model, contents=prompt, config=config)
                text = response.text
            except Exception as exc:  # noqa: BLE001 - any Gemini failure moves on, never breaks the chat turn
                code = nlu._code_of(exc)
                if code == 429 and limits.is_daily_limit(str(exc)):
                    limits.block(key, limits.seconds_until_pacific_midnight())
                elif nlu._is_transient(exc):
                    transient = True
                logger.warning("llm_provider=gemini model=%s error=%s, trying the next provider", model, code or type(exc).__name__)
                continue
            if not text:
                logger.warning("llm_provider=gemini model=%s empty_response", model)
                continue
            nlu._record(True, False)
            usage = getattr(response, "usage_metadata", None)
            logger.info("llm_provider=gemini model=%s prompt_tokens=%s", model, getattr(usage, "prompt_token_count", "?"))
            return text
        if transient:
            nlu._record(False, True)
        raise ProviderUnavailable("gemini: no model answered")
