import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

from ..config import settings
from ..nlu import llm_understander as nlu
from . import limits
from .base import BaseLLM, ProviderUnavailable

logger = logging.getLogger(__name__)

# The SDK's own deadline cannot go below 10 s, so the shorter generation timeout is enforced here.
# Separate from the NLU pool so a hung generation call never starves the understanding layer.
_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="gemini-gen")


def _call(model: str, prompt: str, config):
    return nlu._get_client().models.generate_content(model=model, contents=prompt, config=config)


class GeminiProvider(BaseLLM):
    """Gemini answer generation: GEMINI_MODEL, then GEMINI_MODEL_FALLBACK.

    Only the system prompt and the prompt (question + retrieved scheme text) are sent. It shares the
    daily cap, circuit breaker and client of the NLU layer, so one key budget covers both. Each request
    gets GEMINI_GEN_TIMEOUT seconds; a timeout, 429 or 5xx hands over to the next provider at once with
    no retry delay and counts towards the breaker. A model whose daily quota is used up is skipped until
    the reset and the other Gemini model is tried. When nothing answers it raises ProviderUnavailable.
    """

    name = "gemini"

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
        for model in models:
            key = f"gemini:{model}"
            if limits.is_blocked(key):
                logger.info("llm_provider=gemini model=%s skipped (daily limit)", model)
                continue
            if not nlu.reserve_daily():
                logger.warning("llm_provider=gemini daily_cap_reached")
                break
            future = _pool.submit(_call, model, prompt, config)
            try:
                response = future.result(timeout=settings.gemini_gen_timeout)
                text = response.text
            except FutureTimeout:
                nlu._record(False, True)
                logger.warning("llm_provider=gemini model=%s timeout after %.1fs, trying the next provider", model, settings.gemini_gen_timeout)
                raise ProviderUnavailable("gemini: timeout")
            except Exception as exc:  # noqa: BLE001 - any Gemini failure moves on, never breaks the chat turn
                code = nlu._code_of(exc)
                if code == 429 and limits.is_daily_limit(str(exc)):
                    limits.block(key, limits.seconds_until_pacific_midnight())
                    continue  # this model's quota is gone; the other one has its own
                if nlu._is_transient(exc):
                    nlu._record(False, True)
                    logger.warning("llm_provider=gemini model=%s error=%s, trying the next provider", model, code or type(exc).__name__)
                    raise ProviderUnavailable(f"gemini: {code or type(exc).__name__}")
                logger.warning("llm_provider=gemini model=%s error=%s, trying the next model", model, code or type(exc).__name__)
                continue
            if not text:
                logger.warning("llm_provider=gemini model=%s empty_response", model)
                continue
            nlu._record(True, False)
            usage = getattr(response, "usage_metadata", None)
            logger.info("llm_provider=gemini model=%s prompt_tokens=%s", model, getattr(usage, "prompt_token_count", "?"))
            return text
        raise ProviderUnavailable("gemini: no model answered")
