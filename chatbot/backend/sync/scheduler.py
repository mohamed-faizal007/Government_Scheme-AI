"""Schedule scheme_sync on a timer (daily 02:00 local by default).

    python chatbot/backend/sync/scheduler.py --run-now      # one sync now, then exit
    python chatbot/backend/sync/scheduler.py                # foreground scheduler process
    python chatbot/backend/sync/scheduler.py --dry-run --run-now

The FastAPI app imports start_scheduler() so the schedule runs on a background
thread inside the API process; a sync never runs on the request path.
"""
import argparse
import logging
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

# Allow running as a plain script (python scheduler.py) as well as a module.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from apscheduler.schedulers.background import BackgroundScheduler  # noqa: E402
from apscheduler.triggers.cron import CronTrigger  # noqa: E402

from chatbot.backend.sync.scheme_sync import run_sync  # noqa: E402

logger = logging.getLogger("sync_scheduler")

JOB_ID = "scheme_sync"
DEFAULT_HOUR = 2
DEFAULT_MINUTE = 0

_scheduler: BackgroundScheduler | None = None


def start_scheduler(hour: int = DEFAULT_HOUR, minute: int = DEFAULT_MINUTE) -> BackgroundScheduler | None:
    """Start the background scheduler (idempotent). Returns None if it cannot start."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return _scheduler
    try:
        scheduler = BackgroundScheduler(daemon=True)
        scheduler.add_job(
            run_sync,
            CronTrigger(hour=hour, minute=minute),
            id=JOB_ID,
            max_instances=1,  # never overlap two syncs
            coalesce=True,
            misfire_grace_time=3600,
        )
        scheduler.start()
        _scheduler = scheduler
        logger.info("Scheme sync scheduled daily at %02d:%02d; next run: %s", hour, minute, get_next_run_time())
        return scheduler
    except Exception:
        logger.exception("Could not start the sync scheduler; continuing without it")
        return None


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None


def get_next_run_time() -> datetime | None:
    if _scheduler is None or not _scheduler.running:
        return None
    job = _scheduler.get_job(JOB_ID)
    return getattr(job, "next_run_time", None) if job else None


def next_default_run(now: datetime | None = None) -> datetime:
    """Next 02:00 local, for reporting when the scheduler isn't running in this process."""
    now = now or datetime.now()
    candidate = now.replace(hour=DEFAULT_HOUR, minute=DEFAULT_MINUTE, second=0, microsecond=0)
    return candidate if candidate > now else candidate + timedelta(days=1)


def trigger_sync_in_background() -> threading.Thread:
    """Fire one sync on its own thread and return immediately."""
    thread = threading.Thread(target=run_sync, name="manual-sync", daemon=True)
    thread.start()
    return thread


def main() -> int:
    parser = argparse.ArgumentParser(description="Scheme sync scheduler")
    parser.add_argument("--run-now", action="store_true", help="run one sync immediately and exit")
    parser.add_argument("--dry-run", action="store_true", help="with --run-now: report only, write nothing")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.run_now:
        run_sync(dry_run=args.dry_run)
        return 0

    if start_scheduler() is None:
        return 1
    try:
        while True:
            time.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        stop_scheduler()
    return 0


if __name__ == "__main__":
    sys.exit(main())
