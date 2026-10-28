import logging

import requests

from ..config import settings
from .base import BaseLLM, ProviderUnavailable

logger = logging.getLogger(__name__)

TIMEOUT_S = 20  # last resort: past this the user sees the "busy" message instead of waiting


class OllamaProvider(BaseLLM):
    def __init__(self, model: str | None = None, base_url: str | None = None, timeout: float = TIMEOUT_S):
        self.model = model or settings.ollama_model
        self.base_url = base_url or settings.ollama_base_url
        self.timeout = timeout

    def generate(self, prompt: str, system: str = "") -> str:
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "system": system,
                    "stream": False,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            text = response.json()["response"]
        except (requests.RequestException, KeyError, ValueError) as exc:
            raise ProviderUnavailable(f"ollama: {type(exc).__name__}") from exc
        logger.info("llm_provider=ollama model=%s", self.model)
        return text
