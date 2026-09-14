"""End-to-end RAG chain: retrieve -> generate.
Run test: python -m chatbot.backend.rag.rag_chain  (from repo root)
"""
from ..retrieval.retriever import retrieve
from .generator import DECLINE_MESSAGE, generate


def answer(query: str, language: str = "en") -> dict:
    retrieved_schemes = retrieve(query, top_k=5)

    if not retrieved_schemes:
        return {
            "answer": DECLINE_MESSAGE,
            "sources": [],
            "confidence": "low",
            "language": language,
        }

    return generate(query, retrieved_schemes, language=language)


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")

    test_queries = [
        "What documents do I need to apply for PM-KISAN?",
        "What is the benefit amount for housing schemes for SC category?",
        "Tell me about a scheme called XYZ123 that does not exist",
    ]

    for i, q in enumerate(test_queries, start=1):
        print(f"\n=== Test {i}: {q} ===")
        result = answer(q)
        print(f"Confidence: {result['confidence']}")
        print(f"Answer: {result['answer']}")
        print(f"Sources: {result['sources']}")
