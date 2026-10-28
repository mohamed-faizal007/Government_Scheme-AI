"""Remembers which models have used up their daily quota, so later requests skip them until reset.

State is per process and in memory: a restart simply finds out again from the first 429.
"""
import logging
import re
import threading
import time
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_blocked_until: dict[str, float] = {}  # "provider:model" -> unix time when it may be tried again

_DAILY_RE = re.compile(r"per day|perday|\(tpd\)|\(rpd\)|daily", re.IGNORECASE)
_RETRY_IN_RE = re.compile(r"try again in\s+(?:(\d+)h)?\s*(?:(\d+)m(?!s))?\s*(?:([\d.]+)s)?", re.IGNORECASE)


def is_blocked(key: str) -> bool:
    with _lock:
        until = _blocked_until.get(key)
        if until is None:
            return False
        if time.time() >= until:
            del _blocked_until[key]
            return False
        return True


def block(key: str, seconds: float) -> None:
    with _lock:
        _blocked_until[key] = time.time() + seconds
    logger.warning("llm_limits: %s daily limit exhausted, skipping it for %.0f min", key, seconds / 60)


def reset() -> None:
    with _lock:
        _blocked_until.clear()


def is_daily_limit(message: str) -> bool:
    return bool(_DAILY_RE.search(message or ""))


def seconds_until_utc_midnight() -> float:
    now = datetime.now(timezone.utc)
    return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).timestamp() - now.timestamp()


def seconds_until_pacific_midnight() -> float:
    """Gemini's daily quotas reset at midnight Pacific time."""
    try:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo("America/Los_Angeles")
    except Exception:  # noqa: BLE001 - no tz database: assume standard time
        tz = timezone(timedelta(hours=-8))
    now = datetime.now(tz)
    return ((now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0) - now).total_seconds()


def groq_reset_seconds(message: str) -> float:
    """Groq says "Please try again in 7m26.4s"; without that, assume the UTC-midnight reset."""
    match = _RETRY_IN_RE.search(message or "")
    if match and any(match.groups()):
        hours, minutes, seconds = (float(g) if g else 0.0 for g in match.groups())
        return max(hours * 3600 + minutes * 60 + seconds, 1.0)
    return seconds_until_utc_midnight()
