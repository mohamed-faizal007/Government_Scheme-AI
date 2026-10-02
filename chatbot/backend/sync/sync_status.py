"""Read sync state from the sync log files (no MongoDB access, never raises).
Run: python -m chatbot.backend.sync.sync_status  (from repo root)
"""
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

SYNC_LOG_DIR = Path(__file__).resolve().parents[2] / "data" / "sync_logs"
LOCK_FILE = SYNC_LOG_DIR / ".sync_running"
# A lock older than this is assumed to belong to a crashed run.
LOCK_STALE_AFTER = timedelta(hours=2)


def _log_files() -> list[Path]:
    # Names are sync_YYYYMMDD_HHMMSS.json, so lexical order is chronological.
    try:
        return sorted(SYNC_LOG_DIR.glob("sync_*.json"), reverse=True)
    except OSError:
        return []


def _read_report(path: Path) -> dict | None:
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def get_latest_report(successful_only: bool = False) -> dict | None:
    for path in _log_files():
        report = _read_report(path)
        if report is None:
            continue
        if successful_only and report.get("status", "success") == "failed":
            continue
        return report
    return None


def acquire_lock() -> bool:
    """Create the 'sync in progress' marker. Returns False if a live run holds it."""
    SYNC_LOG_DIR.mkdir(parents=True, exist_ok=True)
    if is_sync_running():
        return False
    LOCK_FILE.write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")
    return True


def release_lock() -> None:
    try:
        LOCK_FILE.unlink()
    except OSError:
        pass


def is_sync_running() -> bool:
    try:
        started = datetime.fromisoformat(LOCK_FILE.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return False
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - started < LOCK_STALE_AFTER


def get_sync_status() -> dict:
    """Summary of the last successful sync, for the /sync/status endpoint and CLI."""
    report = get_latest_report(successful_only=True)
    last_report = get_latest_report()
    return {
        "last_sync": report.get("sync_timestamp") if report else None,
        "schemes_updated_last_sync": (
            report.get("new_schemes_added", 0) + report.get("schemes_updated", 0) if report else 0
        ),
        "last_sync_failed": bool(last_report and last_report.get("status") == "failed"),
        "sync_in_progress": is_sync_running(),
    }


if __name__ == "__main__":
    print(json.dumps(get_sync_status(), indent=2))
