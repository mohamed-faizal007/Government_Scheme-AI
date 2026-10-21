"""Helpers for cleaning scheme descriptions that begin with MyScheme portal pop-up text."""
import re

# Every extracted description starts with this pop-up sentence, followed by a header run
# (state/ministry + scheme name + tag words) and the literal word "Details", then the real text.
_POPUP_RE = re.compile(
    r"^\s*It seems you have already initiated your application earlier\.\s*To know more please visit\s*",
    re.IGNORECASE,
)
_HEADER_RE = re.compile(r"^(.{0,400}?)Details\s*", re.DOTALL)

# A header run with no "Details" marker is name + tags only (all such runs are under 210 chars).
MAX_HEADER_ONLY_CHARS = 250


def clean_description(text: str | None) -> str:
    """Strip the portal pop-up sentence and the header run that follows it.

    Descriptions that do not start with the pop-up sentence are returned unchanged. If nothing
    but a header run remains (no real description was extracted), the result is an empty string.
    """
    if not text:
        return text or ""
    popup = _POPUP_RE.match(text)
    if not popup:
        return text
    rest = text[popup.end():]
    header = _HEADER_RE.match(rest)
    if header:
        return rest[header.end():].strip()
    if len(rest) <= MAX_HEADER_ONLY_CHARS:
        return ""
    return rest.strip()


# A description shorter than this is a truncated fragment ("The aims and", "ain"), not content.
MIN_DESCRIPTION_CHARS = 40


def has_description_content(text: str | None) -> bool:
    """True when a description carries real text worth embedding on its own."""
    return len((text or "").strip()) >= MIN_DESCRIPTION_CHARS
