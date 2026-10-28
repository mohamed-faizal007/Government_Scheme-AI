from .base import BaseLLM
from .chain import FallbackChain
from .gemini_provider import GeminiProvider
from .groq_provider import GroqProvider
from .ollama_provider import OllamaProvider


def get_llm(provider: str = "groq") -> BaseLLM:
    """"groq" is the full chain: Groq 20b -> Groq 120b -> Gemini -> Ollama."""
    if provider == "groq":
        return FallbackChain([GroqProvider(), GeminiProvider(), OllamaProvider()])
    if provider == "ollama":
        return OllamaProvider()
    raise ValueError(f"Unknown LLM provider: {provider}")
