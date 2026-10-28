"""Delete the saved answer cache.
Run: python -m chatbot.backend.cache.clear_cache  (from repo root; restart a running server afterwards,
since it holds its own copy in memory)
"""
from . import answer_cache

if __name__ == "__main__":
    answer_cache.clear()
    print(f"Cleared {answer_cache.CACHE_FILE}")
