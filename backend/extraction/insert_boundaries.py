import re
from typing import List, Optional

from postprocess import repair_mojibake
from preprocess import HEADINGS as _BASE_HEADINGS

# ==========================================================
# FOOTER NOISE
# ==========================================================
# Literal footer strings observed verbatim in raw extracted text (page
# footer/contact block), contaminating FAQ answers and objectives when
# left in place. Stripped by exact literal match (re.escape'd, so
# regex-special characters like "(", ")", "©", "®", "." are treated as
# literal text, not regex syntax) before boundary insertion or heading
# classification ever sees the text.
#
# Two real-data wrinkles found while validating against actual extracted
# footers (not just the literal strings as originally reported), both
# handled below rather than by changing the reported literal strings
# themselves:
#
#   1. The source text is mojibake (UTF-8 decoded as cp1252, e.g. "©"
#      comes out as "Â©", "®" as "Â®") -- repaired first via
#      postprocess.repair_mojibake so the literal-© match actually lands.
#   2. "(DIC) (Meit" assumes "(DIC)" and "(Meit" are adjacent, but real
#      text has "Ministry of Electronics & IT" glued between them:
#      "(DIC)Ministry of Electronics & IT (MeitY)...". Matched with a
#      distance-bounded gap instead of an exact literal so it still can't
#      runaway-match unrelated content elsewhere in the document.

_FOOTER_NOISE_PHRASES = [
    "No new news and updates available©2024",
    "Y)Government of India®",
    "Get in touch4th Floor",
    "Electronics Niketan, 6 CGO Complex, Lodhi Road, New Delhi - 110003, India",
    "(011) 24303714",
    "v-2.1.1",
]


def _tolerant_pattern(phrase: str) -> str:
    """re.escape each fragment, but allow zero or more whitespace where
    the literal has a space -- real extractions are inconsistent about
    whether "support-" and "myscheme..." are glued or space-separated."""

    fragments = phrase.split(" ")
    return r"\s*".join(re.escape(f) for f in fragments)


_FOOTER_NOISE_REGEX = re.compile(
    "|".join(re.escape(phrase) for phrase in _FOOTER_NOISE_PHRASES)
    + r"|\(DIC\).{0,60}?\(Meit"
    + "|" + _tolerant_pattern("support- myscheme[at]digitalindia[dot]gov[dot]in"),
    re.IGNORECASE,
)


def strip_footer_noise(text: str) -> str:
    """
    Remove known footer strings verbatim (case-insensitive), before any
    boundary insertion or heading classification runs. Repairs mojibake
    first so literal matches against real special characters (©, ®) land.
    """

    return _FOOTER_NOISE_REGEX.sub("", repair_mojibake(text))

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

    footer_sample = "Get in touch4th Floor, Ne GD, Electronics Niketan"
    print("\nFOOTER STRIP TEST:")
    print("BEFORE:", repr(footer_sample))
    print("AFTER: ", repr(strip_footer_noise(footer_sample)))
