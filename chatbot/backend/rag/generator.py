"""LLM answer generation grounded strictly in retrieved scheme content.
Run test: python -m chatbot.backend.rag.generator  (from repo root)
"""
import json
import logging
import re

from ..llm.base import ContextTooLargeError
from ..llm.factory import get_llm

logger = logging.getLogger(__name__)

DECLINE_MESSAGE = (
    "I don't have reliable information on this. Please check the official "
    "MyScheme portal at myscheme.gov.in"
)

UNAVAILABLE_MESSAGE = (
    "I'm currently unable to process your request. Please try again in a "
    "moment or visit myscheme.gov.in for scheme information."
)

# Groq's free tier caps a single request at 8,000 tokens/min per model, so the prompt is
# budgeted well under that: per-scheme text is capped, the whole prompt is capped, and a
# "too large" rejection retries with fewer schemes.
SCHEME_CHAR_CAP = 2500
MAX_PROMPT_TOKENS = 5500
CHARS_PER_TOKEN = 3  # conservative; English runs ~4 chars/token
RETRY_SCHEME_COUNTS = (5, 3, 2)
# Share of SCHEME_CHAR_CAP each section is guaranteed; unused budget goes to later
# sections in order (the FAQ only gets leftovers).
SECTION_SHARES = {"description": 500, "benefits": 400, "eligibility": 350, "application": 250, "faq": 0}

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
- Always write the answer in English, regardless of what language the user's question is \
written in. The question may be in Tamil, Hindi, or another language — always respond in \
English; a separate translation step handles the user's language.

- Cite each scheme using its exact name as written in the context.

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

    sections: dict[str, list[str]] = {key: [] for key in SECTION_SHARES}
    if overview.get("description"):
        sections["description"].append(f"Description: {overview['description']}")
    if benefits.get("financial_assistance"):
        sections["benefits"].append(f"Financial assistance: {benefits['financial_assistance']}")
    if benefits.get("other_benefits"):
        sections["benefits"].append("Other benefits: " + " | ".join(benefits["other_benefits"]))
    if eligibility.get("conditions"):
        sections["eligibility"].append("Eligibility conditions: " + " | ".join(eligibility["conditions"]))
    if eligibility.get("exclusions"):
        sections["eligibility"].append("Eligibility exclusions: " + " | ".join(eligibility["exclusions"]))
    if application.get("documents"):
        sections["application"].append("Required documents: " + " | ".join(application["documents"]))
    if application.get("steps"):
        sections["application"].append("Application steps: " + " | ".join(application["steps"]))
    for item in faq[:5]:
        if item.get("question"):
            sections["faq"].append(f"FAQ - Q: {item['question']} A: {item.get('answer', '')}")

    texts = {key: "\n".join(parts) for key, parts in sections.items()}
    allowed = {key: min(len(text), SECTION_SHARES[key]) for key, text in texts.items()}
    leftover = SCHEME_CHAR_CAP - sum(allowed.values())
    for key, text in texts.items():
        extra = min(len(text) - allowed[key], max(leftover, 0))
        allowed[key] += extra
        leftover -= extra

    lines = [f"### Scheme: {name}"]
    for key, text in texts.items():
        if not text:
            continue
        if len(text) > allowed[key]:
            text = text[: max(allowed[key] - 1, 0)].rstrip() + "…"
        if text:
            lines.append(text)

    return "\n".join(lines)


def _build_prompt(query: str, retrieved_schemes: list[dict]) -> str:
    context = "\n\n".join(_format_scheme_context(hit) for hit in retrieved_schemes)
    return f"""Retrieved scheme content:

{context}

User question: {query}"""


def _estimate_tokens(system_prompt: str, prompt: str) -> int:
    return (len(system_prompt) + len(prompt)) // CHARS_PER_TOKEN


def _fit_to_budget(query: str, schemes: list[dict], system_prompt: str) -> list[dict]:
    """Drop the lowest-ranked schemes until the estimated prompt fits MAX_PROMPT_TOKENS."""
    schemes = list(schemes)
    while len(schemes) > 1 and _estimate_tokens(system_prompt, _build_prompt(query, schemes)) > MAX_PROMPT_TOKENS:
        schemes.pop()
    return schemes


def _scheme_count_ladder(available: int) -> list[int]:
    """Scheme counts to try, largest first: all retrieved, then 3, then 2."""
    return [available] + [n for n in RETRY_SCHEME_COUNTS if n < available]


def generate(
    query: str,
    retrieved_schemes: list[dict],
    language: str = "en",
    system_prompt_suffix: str = "",
) -> dict:
    if not retrieved_schemes:
        return {
            "answer": DECLINE_MESSAGE,
            "sources": [],
            "confidence": "low",
            "language": language,
        }

    system_prompt = SYSTEM_PROMPT + (f"\n\n{system_prompt_suffix}" if system_prompt_suffix else "")

    try:
        llm = get_llm()
        all_schemes = retrieved_schemes
        raw = None
        for count in _scheme_count_ladder(len(all_schemes)):
            retrieved_schemes = _fit_to_budget(query, all_schemes[:count], system_prompt)
            prompt = _build_prompt(query, retrieved_schemes)
            logger.info(
                "generator: schemes_used=%d est_prompt_tokens=%d",
                len(retrieved_schemes),
                _estimate_tokens(system_prompt, prompt),
            )
            try:
                raw = llm.generate(prompt, system=system_prompt)
                break
            except ContextTooLargeError:
                logger.warning("generator: context too large at %d schemes, retrying with fewer", len(retrieved_schemes))
        if raw is None:
            raise ContextTooLargeError("prompt too large even at the smallest scheme count")
    except Exception:
        logger.exception("generator: LLM generation failed after all fallbacks")
        return {
            "answer": UNAVAILABLE_MESSAGE,
            "sources": [],
            "confidence": "low",
            "language": language,
        }

    answer, confidence = _parse_response(raw)

    # Grounding check: an answer that names none of the retrieved schemes was produced
    # from the LLM's own knowledge (e.g. "Paris"), not from context. This applies at any
    # reported confidence — the LLM labelled "Paris" as "medium" in the 2026-10-10 eval.
    if not any(names_scheme(answer, hit.get("scheme_name", "")) for hit in retrieved_schemes):
        logger.warning("generator: citation_guard=declined (answer names no retrieved scheme, confidence=%s)", confidence)
        answer = DECLINE_MESSAGE
    else:
        logger.info("generator: citation_guard=passed")

    declined = DECLINE_MESSAGE.strip().lower() in answer.strip().lower()
    sources = []
    used_schemes = []
    if not declined:
        seen = set()
        for hit in retrieved_schemes:
            if names_scheme(answer, hit.get("scheme_name", "")) and hit["scheme"].get("_id"):
                used_schemes.append({"id": str(hit["scheme"]["_id"]), "name": hit["scheme_name"]})
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
        "used_schemes": used_schemes,  # cited schemes with ids; the API keeps them for follow-ups
    }


_HYPHENS = ("‐", "‑", "‒", "–", "—", "−")
_QUOTES = {"‘": "'", "’": "'", "“": '"', "”": '"'}
_EDGE_PUNCT_RE = re.compile(r"^[\W_]+|[\W_]+$")
MIN_NAME_CHARS = 4  # shorter normalised names ("E.", "'") would match by accident


def _normalize_for_match(text: str) -> str:
    """Lowercase, unify Unicode hyphens/quotes, collapse spaces, strip edge punctuation.

    LLMs emit non-breaking/typographic hyphens and odd spacing, and some stored scheme names carry
    stray trailing punctuation ("Abhayakiranam Scheme-"); both defeat plain substring matching.
    """
    for dash in _HYPHENS:
        text = text.replace(dash, "-")
    for fancy, plain in _QUOTES.items():
        text = text.replace(fancy, plain)
    return _EDGE_PUNCT_RE.sub("", " ".join(text.lower().split()))


def names_scheme(answer: str, scheme_name: str) -> bool:
    """True when `answer` names `scheme_name` (both normalised; stored names are not modified)."""
    name = _normalize_for_match(scheme_name or "")
    if len(name) < MIN_NAME_CHARS:
        return False
    return name in _normalize_for_match(answer)


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
