"""Answer cache: (normalised question, answer language, pill language) -> a guard-passed answer.

In memory, mirrored to chatbot/data/answer_cache.json (gitignored) so it survives a restart. At most
MAX_ENTRIES entries, each valid for TTL_S. The caller decides what may be stored; this module only
keeps entries. Clear it with: python -m chatbot.backend.cache.clear_cache  (then restart the server).
"""
import copy
import json
import logging
import os
import re
import threading
import time
import unicodedata
from pathlib import Path

from ..config import settings

logger = logging.getLogger(__name__)

MAX_ENTRIES = 500
TTL_S = 24 * 3600
CACHE_FILE = Path(__file__).resolve().parents[2] / "data" / "answer_cache.json"

_lock = threading.Lock()
_entries: dict[str, dict] | None = None  # key -> {"t": stored-at unix time, "v": value}; oldest first


def enabled() -> bool:
    return settings.answer_cache


def make_key(question: str, language: str, pill: str | None) -> str:
    text = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", question).lower()).strip(" ?!.,;:।")
    return "\x1f".join((text, language, pill or ""))


def _load() -> dict[str, dict]:
    global _entries
    if _entries is None:
        _entries = {}
        try:
            raw = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            now = time.time()
            _entries = {k: e for k, e in raw.items() if now - e["t"] < TTL_S}
        except FileNotFoundError:
            pass
        except Exception:  # noqa: BLE001 - a corrupt file just means an empty cache
            logger.exception("answer_cache: could not read %s, starting empty", CACHE_FILE)
    return _entries


def _save(entries: dict[str, dict]) -> None:
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = CACHE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, CACHE_FILE)
    except Exception:  # noqa: BLE001 - persistence is best effort; the in-memory cache still works
        logger.exception("answer_cache: could not write %s", CACHE_FILE)


def get(key: str) -> dict | None:
    with _lock:
        entry = _load().get(key)
        if entry is None:
            return None
        if time.time() - entry["t"] >= TTL_S:
            del _entries[key]
            return None
        return copy.deepcopy(entry["v"])


def put(key: str, value: dict) -> None:
    with _lock:
        entries = _load()
        entries.pop(key, None)
        entries[key] = {"t": time.time(), "v": copy.deepcopy(value)}
        while len(entries) > MAX_ENTRIES:
            del entries[next(iter(entries))]
        _save(entries)


def clear() -> None:
    global _entries
    with _lock:
        _entries = {}
        try:
            CACHE_FILE.unlink()
        except FileNotFoundError:
            pass
