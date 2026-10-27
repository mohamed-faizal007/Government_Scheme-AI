"""Follow-up detection: "who can apply for it?" refers to the schemes the bot just listed."""
import re

MAX_REMEMBERED_SCHEMES = 5

_ORDINALS = {
    "first": 0, "1st": 0, "second": 1, "2nd": 1, "third": 2, "3rd": 2,
    "fourth": 3, "4th": 3, "fifth": 4, "5th": 4,
}
_ORDINAL_RE = re.compile(
    r"\b(?:the\s+)?(first|second|third|fourth|fifth|1st|2nd|3rd|4th|5th)\s+(?:one|scheme)\b", re.IGNORECASE
)
_LAST_RE = re.compile(r"\b(?:the\s+)?last\s+(?:one|scheme)\b", re.IGNORECASE)
_PRONOUN_RE = re.compile(
    r"\b(?:it|this|that|this\s+scheme|that\s+scheme|these|those|them|its|the\s+scheme)\b", re.IGNORECASE
)
# A question about some aspect of a scheme, which is a follow-up only when it names no scheme itself.
_DETAIL_RE = re.compile(
    r"who\s+(?:can|is|are|all)|how\s+(?:to|can\s+i|do\s+i)\s+apply|\bapply\b|eligib|documents?|"
    r"\bbenefits?\b|\bamount\b|how\s+much|tell\s+me\s+more|\bmore\s+(?:details?|info|about)|\bdetails?\b|"
    r"\bdeadline\b|last\s+date|\bexplain\b|what\s+is\s+(?:it|this|that)|\bwhat\s+does\b",
    re.IGNORECASE,
)
# Words that carry no topic of their own; if nothing else is left, the message names no subject.
_FILLER = frozenset(
    "who can is are all apply applying for how to do i it its this that these those them the a an of "
    "about on in me my tell more details detail info information documents document needed need required "
    "require what which scheme schemes benefits benefit eligibility eligible criteria please explain "
    "first second third fourth fifth last one amount much does and or also".split()
)


def ordinal_index(message: str, count: int) -> int | None:
    """0-based index when the message says "the first one" / "the last scheme", else None."""
    if _LAST_RE.search(message):
        return count - 1 if count else None
    match = _ORDINAL_RE.search(message)
    if match:
        idx = _ORDINALS[match.group(1).lower()]
        return idx if idx < count else None
    return None


def is_followup(message: str, last_schemes: list, names_scheme: bool) -> bool:
    """True when `message` asks about the previously listed schemes rather than something new."""
    if not last_schemes or names_scheme:
        return False
    if ordinal_index(message, len(last_schemes)) is not None:
        return True
    if not _DETAIL_RE.search(message):
        return False
    if _PRONOUN_RE.search(message):
        return True
    words = re.findall(r"[a-z0-9]+", message.lower())
    return all(w in _FILLER for w in words)
