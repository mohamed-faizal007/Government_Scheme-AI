import re
from pathlib import Path
from typing import List

from postprocess import repair_mojibake

# ==========================================================
# SEMANTIC SECTION HEADINGS
# ==========================================================
# These are structural markers inside the scheme content itself, not noise.
# They are only ever used to insert paragraph breaks (see the bottom of
# preprocess_text). They must never be deleted -- doing so both destroys
# real structure and silently turns the heading-insertion step into a
# no-op (there is nothing left to insert a break in front of).

HEADINGS = [
    "Introduction:",
    "Benefits",
    "Eligibility",
    "Exclusions",
    "Application Process",
    "Documents Required",
    "Frequently Asked Questions",
    "Sources And References",
]

_HEADING_KEYS = {h.lower() for h in HEADINGS}

# ==========================================================
# UI / WEBPAGE NOISE
# ==========================================================
# Loaded from backend/config/ui_noise_patterns.txt when available (falls
# back to a small built-in list if that file is missing). Any entry that
# matches something in HEADINGS is dropped automatically, so a noise list
# can never delete real section structure -- no matter what gets added to
# the config file later.
#
# "Eng" / "English" used to be in this list to strip a language-toggle
# label. They have been removed outright rather than "fixed": a 3-6
# character fragment cannot be matched safely at any word-boundary width
# without also matching real words that legitimately start with it
# ("Engineer", "England", "Bengal", ...). Per PROJECT_PLAN.md Rule 7
# ("do not blindly remove text based on keywords"), it is better to leave
# a rare, harmless UI label in the text than to risk corrupting content.

_NOISE_CONFIG_PATH = (
    Path(__file__).resolve().parents[1] / "config" / "ui_noise_patterns.txt"
)

_FALLBACK_REMOVE_PHRASES = [
    "Are you sure you want to sign out?",
    "Cancel",
    "Sign Out",
    "Sign In",
    "Feedback",
    "Something went wrong.",
    "Please try again later.",
    "Apply Now",
    "Check Eligibility",
    "Back",
    "Was this helpful?",
]


def _load_remove_phrases() -> List[str]:
    phrases = _FALLBACK_REMOVE_PHRASES

    if _NOISE_CONFIG_PATH.exists():
        file_phrases = [
            line.strip()
            for line in _NOISE_CONFIG_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if file_phrases:
            phrases = file_phrases

    # Safety net: never let a noise phrase remove a real content heading.
    return [phrase for phrase in phrases if phrase.lower() not in _HEADING_KEYS]


REMOVE_PHRASES = _load_remove_phrases()


def _phrase_pattern(phrase: str) -> str:
    """
    Build a regex for `phrase` that:
      - never matches as a fragment inside a larger word, and
      - for multi-word phrases, also matches when PDF/webpage extraction
        glued the words together with no space at all, on either side --
        e.g. "...textApplicationProcessStep 1..." -- the exact "Bad
        Spacing" artifact PROJECT_PLAN.md section 6.1 calls out
        ("DetailsIntroduction", "ApplicationProcess", ...).

    The old code used a plain text.replace(), a raw substring match:
    removing "Eng" turned "Engineer" into "ineer" and "England" into
    "land". Here, a boundary is either a genuine non-word character (or
    start/end of string) OR a lowercase/digit -> uppercase transition --
    normal English prose does not glue an uppercase letter directly onto
    an unrelated word, so this still cannot match inside a real word like
    "Engineer", but it does catch two glued, differently-cased UI labels
    like "CancelSign" or "ApplicationProcessStep".
    """

    words = [re.escape(word) for word in phrase.split(" ")]
    body = r"\s*".join(words)

    left = r"(?:(?<!\w)|(?<=[a-z0-9]))"
    right = r"(?:(?!\w)|(?=[A-Z]))"

    return left + body + right


def _replace_whole_phrase(text: str, phrase: str, replacement) -> str:
    return re.sub(_phrase_pattern(phrase), replacement, text)


def preprocess_text(text: str) -> str:
    """
    Clean noisy text extracted from MyScheme PDFs.
    """

    if not text:
        return ""

    # -------------------------------
    # Repair mojibake before anything else
    # -------------------------------
    # Some source PDFs yield UTF-8-decoded-as-cp1252 mojibake straight out
    # of PyMuPDF (e.g. the rupee sign comes out as "â‚¹"). Fixing it here,
    # before the text ever reaches the LLM, means the model reasons over
    # the real character instead of being trusted to echo a byte-mangled
    # sequence back verbatim.

    text = repair_mojibake(text)

    # -------------------------------
    # Normalize whitespace
    # -------------------------------

    text = text.replace("\r", "\n")
    text = re.sub(r"\s+", " ", text)

    # -------------------------------
    # Remove common UI phrases
    # -------------------------------

    for phrase in REMOVE_PHRASES:
        text = _replace_whole_phrase(text, phrase, "")

    # -------------------------------
    # Remove repeated spaces
    # -------------------------------

    text = re.sub(r" {2,}", " ", text)

    # -------------------------------
    # Try to separate headings
    # -------------------------------

    for heading in HEADINGS:
        # Use the canonical heading text (not the raw match) as the
        # replacement, so a glued match like "ApplicationProcess" is
        # normalized to "Application Process" in the output.
        text = _replace_whole_phrase(text, heading, f"\n\n{heading}\n")

    return text.strip()
