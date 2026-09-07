import re
from typing import Dict, List, Tuple

from insert_boundaries import (
    SECTION_DELIMITER,
    WORD_BOUNDARY_DELIMITER,
    leading_heading_match,
)

_WHITESPACE_RUN = re.compile(r"\s+")


def split_into_sections(text: str) -> Tuple[str, List[Tuple[str, str]]]:
    """
    Split boundary-inserted text on SECTION_DELIMITER.

    Returns (preamble, sections):
      - preamble: whatever came before the first detected heading (often
        the scheme's own title/nav chrome).
      - sections: ordered list of (heading_text, content_text). heading_text
        is the exact vocabulary match that triggered the split (whitespace
        collapsed for readability/embedding); content_text is everything
        verbatim up to the next section boundary.
    """

    chunks = text.split(SECTION_DELIMITER)

    preamble = chunks[0].strip()
    sections: List[Tuple[str, str]] = []

    for chunk in chunks[1:]:
        match = leading_heading_match(chunk)

        if not match:
            # Defensive fallback -- every chunk after a split should start
            # with the match that triggered it. If not, keep the content
            # with no heading rather than dropping it.
            sections.append(("", chunk.strip()))
            continue

        heading_text = _WHITESPACE_RUN.sub(" ", match.group(0)).strip()
        content_text = chunk[match.end():].strip()
        sections.append((heading_text, content_text))

    return preamble, sections


def content_items(content_text: str) -> List[str]:
    """Split section content on the word-boundary delimiter into a list
    of verbatim items/lines, dropping empties."""

    items = [line.strip() for line in content_text.split(WORD_BOUNDARY_DELIMITER)]
    return [item for item in items if item]


def collect_sections_by_category(
    sections: List[Tuple[str, str]],
    classifications: List[Dict],
) -> Dict[str, List[str]]:
    """
    Merge every confidently-classified heading's verbatim content into its
    matched category, concatenating in document order when more than one
    heading maps to the same category.
    """

    by_category: Dict[str, List[str]] = {}

    for (heading_text, content_text), classification in zip(sections, classifications):
        if not classification["confident"]:
            continue

        category = classification["category"]
        by_category.setdefault(category, []).extend(content_items(content_text))

    return by_category


def extract_faq_pairs(lines: List[str]) -> List[Dict[str, str]]:
    """
    Rule-based Q/A pairing: a line ending in "?" starts a new question;
    every following line (until the next "?" line) is appended verbatim
    as its answer. No rephrasing.
    """

    faqs: List[Dict[str, str]] = []
    current_question = None
    current_answer_parts: List[str] = []

    def flush():
        if current_question is not None:
            faqs.append({
                "question": current_question,
                "answer": " ".join(current_answer_parts).strip(),
            })

    for line in lines:
        if line.strip().endswith("?"):
            flush()
            current_question = line
            current_answer_parts = []
        elif current_question is not None:
            current_answer_parts.append(line)
        # lines before the first "?" (no question yet) are dropped --
        # there is nothing verbatim-correct to attach them to.

    flush()

    return faqs
