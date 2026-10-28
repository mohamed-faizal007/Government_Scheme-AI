"""Typo tolerance for the deterministic router, without any LLM call.

Fixes (1) state names run together or misspelled by a space ("tamilnadu" -> "Tamil Nadu") and
(2) misspelled scheme-domain keywords ("shcemes", "elegible", "requierd") by fuzzy matching against a
small vocabulary. Only Latin-script text is touched, and only words of 4+ letters that start with the
same letter as the vocabulary word, so ordinary words and acronyms are left alone.
"""
import re
from difflib import get_close_matches

from ..database.load_chroma import STATE_NAMES

VOCABULARY = (
    "scheme", "schemes", "farmer", "farmers", "student", "students", "scholarship", "scholarships", "pension",
    "subsidy", "benefit", "benefits", "eligible", "eligibility", "document", "documents", "required", "available",
    "apply", "application", "about", "government", "which", "explain", "housing", "education", "health", "women",
    "woman", "widow", "widows", "loan", "details", "process", "tell", "criteria", "disability", "unemployed",
)
# Real words that sit close to a vocabulary word and must not be "corrected".
_KEEP = frozenset(
    "former apple tells applied applies applying school schools heath wishes divorce issue about's whole ".split()
)
_CUTOFF = 0.8
_WORD_RE = re.compile(r"[A-Za-z]{4,}")


def _state_patterns():
    # "tamilnadu", "andhrapradesh", "uttar-pradesh" -> the canonical spaced name
    return [(re.compile(rf"\b{re.escape(n.lower()).replace(r'\ ', r'[\s-]?')}\b", re.IGNORECASE), n) for n in STATE_NAMES if " " in n]


_STATE_RES = None


def _fix_word(match: re.Match) -> str:
    word = match.group(0)
    lower = word.lower()
    if lower in VOCABULARY or lower in _KEEP or word.isupper():
        return word
    candidates = [v for v in VOCABULARY if v[0] == lower[0] and abs(len(v) - len(lower)) <= 2]
    close = get_close_matches(lower, candidates, n=1, cutoff=_CUTOFF)
    return close[0] if close else word


def fix_typos(text: str) -> str:
    """`text` with run-together state names and misspelled keywords corrected (unchanged if non-Latin)."""
    global _STATE_RES
    if not text or any(ord(ch) > 0x2FF for ch in text):
        return text
    if _STATE_RES is None:
        _STATE_RES = _state_patterns()
    for pattern, name in _STATE_RES:
        text = pattern.sub(name, text)
    return _WORD_RE.sub(_fix_word, text)
