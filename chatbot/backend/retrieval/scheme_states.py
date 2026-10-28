"""Which state(s) a scheme belongs to, derived from its text, for narrowing eligibility searches.

The data has no structured state: Mongo `metadata.state` is empty for every scheme and ChromaDB's `state` is only
set on eligibility chunks (first state name found in the conditions). So a scheme's states are the state names that
appear in its name or eligibility conditions (whole words only: "goal" is not Goa). A scheme naming no state is
treated as central / state-unspecified; the data cannot tell those two apart.
Run: python -m chatbot.backend.retrieval.scheme_states  (from repo root; prints the counts)
"""
import re

from ..database.load_chroma import STATE_NAMES

_STATE_RE = re.compile(r"\b(" + "|".join(re.escape(s) for s in STATE_NAMES) + r")\b", re.IGNORECASE)
_CANONICAL = {s.lower(): s for s in STATE_NAMES}

_index: dict[str, frozenset[str]] | None = None


def states_in(text: str) -> set[str]:
    return {_CANONICAL[m.lower()] for m in _STATE_RE.findall(text or "")}


def scheme_states(doc: dict) -> frozenset[str]:
    conditions = " ".join((doc.get("eligibility", {}) or {}).get("conditions", []) or [])
    name = (doc.get("metadata", {}) or {}).get("scheme_name", "") or ""
    return frozenset(states_in(name) | states_in(conditions))


def build_index(docs) -> dict[str, frozenset[str]]:
    """scheme id (str) -> its states (empty set = central / unspecified)."""
    return {str(doc["_id"]): scheme_states(doc) for doc in docs}


def get_index() -> dict[str, frozenset[str]]:
    global _index
    if _index is None:
        from ..database.mongo_client import get_schemes_collection

        _index = build_index(get_schemes_collection().find({}, {"metadata.scheme_name": 1, "eligibility.conditions": 1}))
    return _index


def scope_for_state(index: dict[str, frozenset[str]], state: str) -> dict:
    """The user's state's schemes plus central ones: {"ids", "state_count", "central_count"}."""
    wanted = state.strip().lower()
    state_ids = [i for i, st in index.items() if any(s.lower() == wanted for s in st)]
    central_ids = [i for i, st in index.items() if not st]
    return {"ids": state_ids + central_ids, "state_count": len(state_ids), "central_count": len(central_ids)}


if __name__ == "__main__":
    import collections
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    counts = collections.Counter()
    for sts in get_index().values():
        counts["<none: central/unspecified>" if not sts else ("<several>" if len(sts) > 1 else next(iter(sts)))] += 1
    for value, n in counts.most_common():
        print(f"{n:5d}  {value}")
