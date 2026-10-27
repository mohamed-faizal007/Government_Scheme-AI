"""Known scheme names, for routing messages that name a scheme but use no trigger phrase.

Names are normalised exactly like the citation guard (names_scheme), with the same minimum length.
The index is loaded once from MongoDB; if that fails the lookup returns nothing and routing falls
back to the pattern rules.
"""
import logging
import re

from ..database.mongo_client import get_schemes_collection
from ..rag.generator import MIN_NAME_CHARS, _normalize_for_match

logger = logging.getLogger(__name__)

# A name made only of these words ("Scheme For") would match ordinary questions ("Is there a scheme for me?").
_GENERIC_WORDS = frozenset(
    "scheme schemes for the of and in to a an on by with yojana yojna programme program mission".split()
)

_index: list[tuple[str, str, str]] | None = None  # (normalised name, scheme id, display name)


def _load_index() -> list[tuple[str, str, str]]:
    global _index
    if _index is None:
        try:
            docs = get_schemes_collection().find({}, {"metadata.scheme_name": 1})
            entries = []
            for doc in docs:
                name = (doc.get("metadata") or {}).get("scheme_name") or ""
                norm = _normalize_for_match(name)
                if len(norm) >= MIN_NAME_CHARS and set(re.findall(r"\w+", norm)) - _GENERIC_WORDS:
                    entries.append((norm, str(doc["_id"]), name))
            _index = entries
        except Exception:
            logger.exception("scheme_names: could not load the scheme-name index")
            return []  # not cached: retry on the next message
    return _index


def find_schemes_in(text: str, limit: int = 3) -> list[dict]:
    """Schemes whose full name appears in `text`, longest names first.

    A name that is only part of a longer matched name ("Scholarship" inside "Post Matric
    Scholarship") is dropped, so the most specific scheme wins.
    """
    haystack = _normalize_for_match(text)
    if not haystack:
        return []
    found = []
    for norm, scheme_id, name in _load_index():
        if norm in haystack and re.search(rf"(?<!\w){re.escape(norm)}(?!\w)", haystack):
            found.append((norm, scheme_id, name))
    found.sort(key=lambda f: len(f[0]), reverse=True)
    kept: list[tuple[str, str, str]] = []
    for norm, scheme_id, name in found:
        if any(norm in other[0] for other in kept) or any(scheme_id == k[1] for k in kept):
            continue
        kept.append((norm, scheme_id, name))
    return [{"id": scheme_id, "name": name} for _, scheme_id, name in kept[:limit]]
