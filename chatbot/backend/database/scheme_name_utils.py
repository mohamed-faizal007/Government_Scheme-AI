"""Helpers for cleaning scheme names scraped with trailing UI text."""
import re

# Trailing sign-out UI text, optionally wrapped in markdown emphasis (** / __) and whitespace.
_UI_SUFFIX_RE = re.compile(
    r"[\s*_]*(?:are\s+you\s+sure\s+you\s+want\s+to\s+sign\s*out\s*\??|sign\s*out)[\s*_]*$",
    re.IGNORECASE,
)


def clean_scheme_name(name: str | None) -> str:
    """Strip trailing UI text such as 'Are you sure you want to sign out?' or 'Sign Out'.

    Names without such a suffix are returned unchanged (including their original whitespace).
    """
    if not name:
        return name or ""
    match = _UI_SUFFIX_RE.search(name)
    if not match:
        return name
    return name[: match.start()].rstrip(" \t\r\n*_")
