"""Deterministic keyword/regex intent router — no LLM call, so it's fast and reproducible.
Run test: python -m chatbot.backend.router.intent_classifier  (from repo root)
"""
import re

from ..database.load_chroma import STATE_NAMES

ELIGIBILITY_PATTERNS = [
    r"am i eligible", r"do i qualify", r"can i apply", r"check eligibility", r"eligible for",
]

DOCUMENT_PATTERNS = [
    r"\bupload\b", r"verify document", r"check my document", r"my certificate",
]

COMPARISON_PATTERNS = [
    r"\bcompare\b", r"difference between", r"which is better", r"\bvs\b",
]

SCHEME_SEARCH_PATTERNS = [
    r"what is", r"tell me about", r"how to apply", r"schemes for", r"benefits of",
    r"documents required", r"schemes? (?:are|is)?\s*available", r"available for",
    r"\bexplain\b", r"\bwhat\s+(?:documents|identity|proof|benefits)\b",
    r"\bdocuments?\b.*\b(?:required|needed|need)\b", r"\b(?:need|require)\b.*\bdocuments?\b",
    r"how much\b", r"how do i (?:claim|get)\b", r"what does\b.*\bprovide\b",
    r"what benefits\b", r"\bwhich scheme\b",
]

CATEGORY_PATTERNS = {
    "sc": r"\bsc\b|scheduled caste",
    "st": r"\bst\b|scheduled tribe",
    "obc": r"\bobc\b|other backward class",
    "general": r"\bgeneral category\b",
}

GENDER_PATTERNS = {
    "female": r"\bfemale\b|\bwoman\b|\bi\s*am\s*a?\s*girl\b",
    "male": r"\bmale\b|\bman\b|\bi\s*am\s*a?\s*boy\b",
    "other": r"\bnon[- ]binary\b|\bother gender\b|\btransgender\b",
}

AGE_PATTERNS = [
    r"\bi\s*am\s*(\d{1,3})\s*years?\s*old\b",
    r"\bage\s*(?:is|:)?\s*(\d{1,3})\b",
    r"\b(\d{1,3})\s*years?\s*old\b",
]

INCOME_PATTERNS = [
    # Keyword-led: "income of/is/: <amount> [lakh|crore]" or "earn <amount> [...]"
    r"income\s*(?:of|is|:)?\s*(?:rs\.?|₹|rupees)?\s*([\d,]+(?:\.\d+)?)\s*(lakh|lakhs|crore|crores)?",
    r"earn\s*(?:rs\.?|₹|rupees)?\s*([\d,]+(?:\.\d+)?)\s*(lakh|lakhs|crore|crores)?",
    # Bare amount with an explicit unit, e.g. "1.2 lakhs", "2 lakh" — no keyword needed.
    r"(?:rs\.?|₹|rupees)?\s*([\d,]+(?:\.\d+)?)\s*(lakh|lakhs|crore|crores)",
    # A message that is *only* a number (optionally comma-grouped/₹-prefixed), e.g.
    # "1,20,000" or "50000" — the typical reply to a direct income question.
    r"^\s*(?:rs\.?|₹|rupees)?\s*([\d,]{4,}(?:\.\d+)?)\s*()$",
]

MULTIPLIERS = {
    "lakh": 100_000,
    "lakhs": 100_000,
    "crore": 10_000_000,
    "crores": 10_000_000,
}


def _match_any(patterns: list[str], query: str) -> bool:
    return any(re.search(p, query, re.IGNORECASE) for p in patterns)


def extract_entities(query: str) -> dict:
    entities = {}

    for state in STATE_NAMES:
        if state.lower() in query.lower():
            entities["state"] = state
            break

    for category, pattern in CATEGORY_PATTERNS.items():
        if re.search(pattern, query, re.IGNORECASE):
            entities["category"] = category
            break

    for gender, pattern in GENDER_PATTERNS.items():
        if re.search(pattern, query, re.IGNORECASE):
            entities["gender"] = gender
            break

    for pattern in AGE_PATTERNS:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            entities["age"] = int(match.group(1))
            break

    for pattern in INCOME_PATTERNS:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            amount = float(match.group(1).replace(",", ""))
            unit = (match.group(2) or "").lower()
            multiplier = MULTIPLIERS.get(unit, 1)
            entities["income"] = amount * multiplier
            break

    return entities


def classify(query: str) -> dict:
    entities = extract_entities(query)

    if _match_any(ELIGIBILITY_PATTERNS, query):
        return {"intent": "eligibility_check", "confidence": 0.9, "extracted_entities": entities}

    if _match_any(DOCUMENT_PATTERNS, query):
        return {"intent": "document_upload", "confidence": 0.9, "extracted_entities": entities}

    if _match_any(COMPARISON_PATTERNS, query):
        return {"intent": "comparison", "confidence": 0.9, "extracted_entities": entities}

    if _match_any(SCHEME_SEARCH_PATTERNS, query):
        return {"intent": "scheme_search", "confidence": 0.9, "extracted_entities": entities}

    return {"intent": "out_of_scope", "confidence": 0.5, "extracted_entities": entities}


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")

    test_queries = [
        "Am I eligible for PM-KISAN?",
        "I want to upload my income certificate",
        "Compare PM-KISAN vs PMAY",
        "What is the Annal Ambedkar Business Champions Scheme?",
        "I am 30 years old, SC category, income of 1.5 lakhs, from Tamil Nadu",
        "asdkjaslkdj random text",
    ]

    for q in test_queries:
        print(f"{q!r} -> {classify(q)}")
