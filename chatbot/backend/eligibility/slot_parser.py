"""Interprets a bare reply ("general", "30", "1.2 lakhs") as the answer to the slot just asked.
Run test: python -m chatbot.backend.eligibility.slot_parser  (from repo root)
"""
import re

from ..database.load_chroma import STATE_NAMES

# States/UTs not in the retrieval list, plus common spellings, mapped to the stored name.
_EXTRA_STATES = {
    "Andaman and Nicobar Islands": ["andaman", "nicobar"],
    "Dadra and Nagar Haveli and Daman and Diu": ["dadra", "daman", "diu"],
    "Odisha": ["orissa"],
    "Tamil Nadu": ["tamilnadu", "tn"],
    "Jammu and Kashmir": ["j&k", "jammu", "kashmir"],
    "Delhi": ["new delhi", "nct of delhi"],
    "Puducherry": ["pondicherry"],
    "Uttarakhand": ["uttaranchal"],
}

EXAMPLES = {
    "age": "for example: 30",
    "state": "for example: Tamil Nadu, Kerala or Delhi",
    "income_annual": "for example: 1.2 lakhs, 120000 or 1,20,000",
    "category": "for example: general, OBC, SC or ST",
    "gender": "for example: male, female or other",
}

SKIP_WORDS = r"^\s*(?:skip|pass|don'?t know|dont know|not sure|prefer not to say|no idea)\s*[.!]*\s*$"

_CATEGORY = [
    ("sc", r"\bsc\b|scheduled\s+castes?"),
    ("st", r"\bst\b|scheduled\s+tribes?"),
    ("obc", r"\bobc\b|other\s+backward|backward\s+class"),
    ("general", r"\bgeneral\b|\bgen\b|\bunreserved\b|\bopen\b|\bur\b"),
]
_GENDER = [
    ("female", r"\bfemale\b|\bwoman\b|\bwomen\b|\bgirl\b|\blady\b"),
    ("male", r"\bmale\b|\bman\b|\bboy\b|\bgentleman\b"),
    ("other", r"\bother\b|\btransgender\b|\bnon[- ]?binary\b"),
]
_UNITS = {"lakh": 100_000, "lakhs": 100_000, "lac": 100_000, "lacs": 100_000,
          "crore": 10_000_000, "crores": 10_000_000, "k": 1_000, "thousand": 1_000}
_NUMBER = re.compile(r"(?:rs\.?|₹|rupees)?\s*(\d[\d,]*(?:\.\d+)?)\s*(lakhs?|lacs?|crores?|thousand|k)?\b", re.IGNORECASE)


def is_skip(text: str) -> bool:
    return bool(re.match(SKIP_WORDS, text, re.IGNORECASE))


def _first_match(options: list[tuple[str, str]], text: str) -> str | None:
    for value, pattern in options:
        if re.search(pattern, text, re.IGNORECASE):
            return value
    return None


def _parse_state(text: str) -> str | None:
    lowered = text.lower()
    for state in STATE_NAMES + list(_EXTRA_STATES):
        if state.lower() in lowered:
            return state
    for state, aliases in _EXTRA_STATES.items():
        if any(re.search(rf"(?<!\w){re.escape(a)}(?!\w)", lowered) for a in aliases):
            return state
    return None


def _parse_age(text: str) -> int | None:
    match = re.search(r"\b(\d{1,3})\b", text)
    if match and 0 < int(match.group(1)) <= 120:
        return int(match.group(1))
    return None


def _parse_income(text: str) -> float | None:
    match = _NUMBER.search(text)
    if not match:
        return None
    amount = float(match.group(1).replace(",", ""))
    unit = (match.group(2) or "").lower()
    value = amount * _UNITS.get(unit, 1)
    # A bare "5" or "30" is ambiguous (lakhs? rupees?), so only unit-less amounts of 1,000+ count.
    if not unit and value < 1_000:
        return None
    return value


def parse_slot_reply(slot: str, text: str):
    """Return the parsed value for `slot`, or None if `text` cannot be read as that slot."""
    if slot == "age":
        return _parse_age(text)
    if slot == "state":
        return _parse_state(text)
    if slot == "income_annual":
        return _parse_income(text)
    if slot == "category":
        return _first_match(_CATEGORY, text)
    if slot == "gender":
        return _first_match(_GENDER, text)
    return None


if __name__ == "__main__":
    for slot, reply in [
        ("category", "general"), ("category", "GEN"), ("category", "Scheduled Caste"),
        ("category", "other backward"), ("category", "banana"), ("state", "Tamil Nadu"),
        ("state", "Orissa"), ("age", "30"), ("income_annual", "1.2 lakhs"),
        ("income_annual", "1,20,000"), ("income_annual", "120000"), ("gender", "female"),
    ]:
        print(f"{slot:14} {reply!r:20} -> {parse_slot_reply(slot, reply)!r}")
