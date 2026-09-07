import re
from typing import List, Optional

from preprocess import HEADINGS as _BASE_HEADINGS

# ==========================================================
# HEADING VOCABULARY
# ==========================================================
# Base vocabulary is reused from preprocess.py's HEADINGS (the canonical
# section markers already validated for the Gemini pipeline), not
# duplicated. Extended with synonyms this dataset is already known to use
# under different wording (see batch_extract_final.py's
# EXTRACTION_PROMPT: "Financial Assistance" instead of "Benefits", "Who
# Can Apply" instead of "Eligibility", ...) -- these don't exist as a
# structured list anywhere else in the codebase, only as prose in a
# prompt string, so they're added here explicitly.

_EXTRA_HEADING_SYNONYMS = [
    "Financial Assistance",
    "Support Available",
    "Who Can Apply",
    "Objectives",
    "FAQs",
    "FAQ",
    "Sources",
]

_seen = set()
HEADING_VOCABULARY: List[str] = []

for _term in list(_BASE_HEADINGS) + _EXTRA_HEADING_SYNONYMS:
    _key = _term.strip().lower().rstrip(":")
    if _key and _key not in _seen:
        _seen.add(_key)
        HEADING_VOCABULARY.append(_term.strip().rstrip(":"))

# ==========================================================
# DELIMITERS
# ==========================================================
# Distinguishable delimiters so downstream code can tell a real,
# vocabulary-anchored section boundary apart from a generic
# lowercase->uppercase safety-net split.

SECTION_DELIMITER = "\n---SECTION---\n"
WORD_BOUNDARY_DELIMITER = "\n"


def _heading_pattern(phrase: str) -> str:
    """
    Match `phrase` anywhere in the text, case-insensitive, tolerating
    zero or more whitespace between its words -- this dataset is known to
    glue multi-word headings together with no space at all (e.g.
    "ApplicationProcess", per preprocess.py's own notes on the same
    artifact).
    """

    words = [re.escape(w) for w in phrase.split()]
    return r"\s*".join(words)


# Longer phrases first, so alternation prefers e.g. "Frequently Asked
# Questions" over any shorter overlapping vocabulary term at the same
# position.
_SORTED_VOCAB = sorted(HEADING_VOCABULARY, key=len, reverse=True)

_HEADING_REGEX = re.compile(
    "|".join(_heading_pattern(term) for term in _SORTED_VOCAB),
    re.IGNORECASE,
)

_WORD_BOUNDARY_REGEX = re.compile(r"(?<=[a-z])(?=[A-Z])|(?<=[.?!])(?=[A-Z])")


def insert_section_boundaries(text: str) -> str:
    """
    Insert SECTION_DELIMITER immediately before every heading-vocabulary
    match, wherever it occurs in the string -- including glued directly
    onto surrounding text with no space on either side. Deliberately no
    word-boundary guard (unlike preprocess.py's noise-phrase matching):
    recall matters more than precision here, since a missed heading loses
    a whole section's boundary, while a spurious match is just an extra
    split the embedding classifier can flag as low-confidence downstream.
    """

    return _HEADING_REGEX.sub(lambda m: SECTION_DELIMITER + m.group(0), text)


def insert_word_boundaries(text: str) -> str:
    """
    Safety net: split at every lowercase->uppercase transition with no
    space between (e.g. "SchemeAre", "OutEnglish"), and at every
    sentence-ending punctuation mark (. ? !) directly followed by an
    uppercase letter with no space (e.g. "scheme.The", "Scheme?North" --
    the dominant glue pattern in this dataset's FAQ blocks, where every
    "Question?Answer...NextQuestion?" run would otherwise stay one
    unsplit blob).
    """

    return _WORD_BOUNDARY_REGEX.sub(WORD_BOUNDARY_DELIMITER, text)


def insert_boundaries(text: str) -> str:
    """
    Full boundary-recovery pass: heading anchors first, then the general
    word-boundary safety net. Must run before any noise stripping -- noise
    removal should operate on text that already has real boundaries.
    """

    text = insert_section_boundaries(text)
    text = insert_word_boundaries(text)
    return text


def leading_heading_match(text: str) -> Optional[re.Match]:
    """
    Return the re.Match for a heading-vocabulary term at the very start of
    `text`, or None. Used to pull the exact matched heading string back
    off a SECTION_DELIMITER-split chunk.
    """

    return _HEADING_REGEX.match(text)


if __name__ == "__main__":
    sample = (
        "25%CapitalInvestmentSubsidySchemeAre you sure you want to sign out?"
        "CancelSign InBenefitsSubsidy of 25% on machinery cost.EligibilityMSME "
        "units only.DocumentsRequiredPAN card.Aadhaar card."
    )

    print("BEFORE:")
    print(sample)
    print("\nAFTER:")
    print(insert_boundaries(sample))
