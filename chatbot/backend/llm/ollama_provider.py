import logging

import requests

from ..config import settings
from .base import BaseLLM

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLM):
    def __init__(self, model: str | None = None, base_url: str | None = None):
        self.model = model or settings.ollama_model
        self.base_url = base_url or settings.ollama_base_url

    def generate(self, prompt: str, system: str = "") -> str:
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "system": system,
                "stream": False,
            },
            timeout=120,
        )
        response.raise_for_status()
        logger.info("llm_provider=ollama model=%s", self.model)
        return response.json()["response"]
