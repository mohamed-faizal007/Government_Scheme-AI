"""Manual smoke test for Phase 1 — LLM factory + embedding abstraction.
Run: python -m chatbot.backend.test_phase1  (from repo root)
"""
from .config import settings
from .embeddings.multilingual_e5 import MultilingualE5Embedder
from .llm.factory import get_llm


def test_llm():
    if not settings.groq_api_key:
        print("GROQ_API_KEY not set — skipping live LLM call. Set chatbot/.env to test.")
        return
    llm = get_llm("groq")
    response = llm.generate("Say hello in one short sentence.", system="You are a helpful assistant.")
    print("LLM response:", response)


def test_embeddings():
    embedder = MultilingualE5Embedder()
    texts = [
        "PM-KISAN provides income support to farmers.",
        "Housing subsidy for economically weaker sections.",
        "விவசாயிகளுக்கான திட்டங்கள்",
    ]
    vectors = embedder.embed_passage(texts)
    print(f"Embedded {len(vectors)} texts, each of dimension {len(vectors[0])}")
    for i, v in enumerate(vectors):
        print(f"  text[{i}] -> shape ({len(v)},)")


if __name__ == "__main__":
    print("=== LLM Factory Test ===")
    test_llm()
    print("\n=== Embedding Test ===")
    test_embeddings()
