"""LLM answer generation grounded strictly in retrieved scheme content.
Run test: python -m chatbot.backend.rag.generator  (from repo root)
"""
import json
import logging

from ..llm.factory import get_llm

logger = logging.getLogger(__name__)

DECLINE_MESSAGE = (
    "I don't have reliable information on this. Please check the official "
    "MyScheme portal at myscheme.gov.in"
)

SYSTEM_PROMPT = """You are a government scheme assistant. You answer ONLY using the \
retrieved scheme content provided below in the user message. You never use outside \
knowledge.

Rules:
- Answer ONLY from the retrieved scheme content provided.
- Every factual claim must name the scheme it came from.
- If the user names a specific scheme and that exact scheme name does not appear in \
any "### Scheme:" header below, you MUST decline — even if similar-sounding or \
related schemes are present. Never invent, describe, or roleplay a "hypothetical" \
or "example" version of a scheme that isn't literally in the retrieved content.
- If the answer is not found in the retrieved content, respond with exactly this \
sentence and nothing else: "%s"
- Never guess, invent, or hallucinate scheme details, amounts, or eligibility criteria.
- Some scheme content may have FAQ text mixed into the benefits section due to a \
known data limitation — treat all content as valid scheme information regardless of \
which field it came from.
- Format the answer as clean readable paragraphs, not excessive bullet points.

Respond with ONLY a JSON object, no other text, in exactly this shape:
{"answer": "<your answer text>", "confidence": "high" | "medium" | "low"}

confidence is "high" if the answer is directly stated in the retrieved content, \
"medium" if it required inference across the content, "low" if you are declining \
because the content does not cover the question.""" % DECLINE_MESSAGE


def _format_scheme_context(hit: dict) -> str:
    scheme = hit["scheme"]
    name = scheme.get("metadata", {}).get("scheme_name", "") or hit.get("scheme_name", "")
    overview = scheme.get("overview", {})
    benefits = scheme.get("benefits", {})
    eligibility = scheme.get("eligibility", {})
    application = scheme.get("application", {})
    faq = scheme.get("faq", []) or []

    lines = [f"### Scheme: {name}"]
    if overview.get("description"):
        lines.append(f"Description: {overview['description']}")
    if benefits.get("financial_assistance"):
        lines.append(f"Financial assistance: {benefits['financial_assistance']}")
    if benefits.get("other_benefits"):
        lines.append("Other benefits: " + " | ".join(benefits["other_benefits"]))
    if eligibility.get("conditions"):
        lines.append("Eligibility conditions: " + " | ".join(eligibility["conditions"]))
    if eligibility.get("exclusions"):
        lines.append("Eligibility exclusions: " + " | ".join(eligibility["exclusions"]))
    if application.get("documents"):
        lines.append("Required documents: " + " | ".join(application["documents"]))
    if application.get("steps"):
        lines.append("Application steps: " + " | ".join(application["steps"]))
    for item in faq[:5]:
        if item.get("question"):
            lines.append(f"FAQ - Q: {item['question']} A: {item.get('answer', '')}")

    return "\n".join(lines)


def generate(query: str, retrieved_schemes: list[dict], language: str = "en") -> dict:
    if not retrieved_schemes:
        return {
            "answer": DECLINE_MESSAGE,
            "sources": [],
            "confidence": "low",
            "language": language,
        }

    context_blocks = [_format_scheme_context(hit) for hit in retrieved_schemes]
    context = "\n\n".join(context_blocks)

    prompt = f"""Retrieved scheme content:

{context}

User question: {query}"""

    llm = get_llm()
    raw = llm.generate(prompt, system=SYSTEM_PROMPT)

    answer, confidence = _parse_response(raw)

    declined = DECLINE_MESSAGE.strip().lower() in answer.strip().lower()
    sources = []
    if not declined:
        seen = set()
        for hit in retrieved_schemes:
            key = (hit["scheme_name"], hit["section"])
            if key in seen:
                continue
            seen.add(key)
            sources.append(
                {
                    "scheme_name": hit["scheme_name"],
                    "section": hit["section"],
                    "source_file": hit["source_file"],
                }
            )
    else:
        confidence = "low"

    return {
        "answer": answer,
        "sources": sources,
        "confidence": confidence,
        "language": language,
    }


def _parse_response(raw: str) -> tuple[str, str]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        data = json.loads(raw)
        answer = data.get("answer", "").strip()
        confidence = data.get("confidence", "medium").strip().lower()
        if confidence not in ("high", "medium", "low"):
            confidence = "medium"
        if answer:
            return answer, confidence
    except (json.JSONDecodeError, AttributeError):
        logger.warning("generator: failed to parse LLM JSON response, using raw text")

    return raw, "medium"


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")

    from ..retrieval.retriever import retrieve

    test_queries = [
        "What documents do I need to apply for PM-KISAN?",
        "What is the benefit amount for housing schemes for SC category?",
        "Tell me about a scheme called XYZ123 that does not exist",
    ]

    for i, q in enumerate(test_queries, start=1):
        print(f"\n=== Test {i}: {q} ===")
        hits = retrieve(q, top_k=3)
        result = generate(q, hits)
        print(f"Confidence: {result['confidence']}")
        print(f"Answer: {result['answer']}")
        print(f"Sources: {result['sources']}")
