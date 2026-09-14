"""Phase 7 verification: language detection + end-to-end translated RAG answers.
Run: python -m chatbot.backend.test_phase7
"""
from .rag.rag_chain import answer
from .translation.translator import detect_language

TEST_CASES = [
    ("Tamil", "விவசாயிகளுக்கான திட்டங்கள் என்ன?"),
    ("Hindi", "किसानों के लिए क्या योजनाएं हैं?"),
    ("English", "What schemes are available for farmers?"),
]


def main():
    for label, query in TEST_CASES:
        print(f"\n=== {label} query ===")
        print(f"Query: {query}")

        language = detect_language(query)
        print(f"Detected language: {language}")

        result = answer(query, language=language)
        print(f"Confidence: {result['confidence']}")
        print(f"Answer ({language}): {result['answer']}")
        print(f"Sources: {result['sources']}")


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    main()
