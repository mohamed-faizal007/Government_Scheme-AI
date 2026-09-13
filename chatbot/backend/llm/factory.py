from .base import BaseLLM
from .groq_provider import GroqProvider
from .ollama_provider import OllamaProvider


def get_llm(provider: str = "groq") -> BaseLLM:
    if provider == "groq":
        return GroqProvider()
    if provider == "ollama":
        return OllamaProvider()
    raise ValueError(f"Unknown LLM provider: {provider}")
