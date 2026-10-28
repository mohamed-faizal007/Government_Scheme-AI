from ..config import settings
from .base import BaseLLM
from .chain import FallbackChain
from .gemini_provider import GeminiProvider
from .groq_provider import GroqProvider
from .ollama_provider import OllamaProvider


def get_llm(provider: str = "groq") -> BaseLLM:
    """"groq" is the full chain. GENERATION_PRIMARY=gemini (default): Gemini -> Groq 20b -> Groq 120b ->
    Ollama; GENERATION_PRIMARY=groq: Groq 20b -> Groq 120b -> Gemini -> Ollama."""
    if provider == "groq":
        if settings.generation_primary == "groq":
            return FallbackChain([GroqProvider(), GeminiProvider(), OllamaProvider()])
        return FallbackChain([GeminiProvider(), GroqProvider(), OllamaProvider()])
    if provider == "ollama":
        return OllamaProvider()
    raise ValueError(f"Unknown LLM provider: {provider}")
