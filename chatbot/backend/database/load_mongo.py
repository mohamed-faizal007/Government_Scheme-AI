"""Load JSONs from dataset/gov_myscheme/test_output_unstructured/ into MongoDB.
Read-only against the source folder; idempotent against MongoDB (matches on source_file).
Run: python -m chatbot.backend.database.load_mongo  (from repo root)
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from pymongo import ASCENDING

from .mongo_client import get_schemes_collection

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SOURCE_DIR = Path("dataset/gov_myscheme/test_output_unstructured")

CORRUPTED_NAME_MARKERS = [
    "are you sure you want to sign out",
]


def load_json_files(source_dir: Path = SOURCE_DIR) -> list[tuple[str, dict]]:
    files = sorted(source_dir.glob("*.json"))
    records = []
    for f in files:
        with open(f, encoding="utf-8") as fh:
            records.append((f.name, json.load(fh)))
    return records


def ensure_indexes(collection) -> None:
    collection.create_index([("scheme_name", ASCENDING)])
    collection.create_index([("source_file", ASCENDING)], unique=True)


def run() -> None:
    collection = get_schemes_collection()
    ensure_indexes(collection)

    records = load_json_files()
    inserted = 0
    skipped = 0
    failed = 0

    for source_file, data in records:
        try:
            scheme_name = data.get("metadata", {}).get("scheme_name", "") or ""
            if any(marker in scheme_name.lower() for marker in CORRUPTED_NAME_MARKERS):
                logger.warning("scheme_name corrupted with UI text in %s: %r", source_file, scheme_name)

            if collection.find_one({"source_file": source_file}):
                skipped += 1
                continue

            doc = dict(data)
            doc["source_file"] = source_file
            doc["ingested_at"] = datetime.now(timezone.utc)
            doc["embedding_status"] = "pending"
            collection.insert_one(doc)
            inserted += 1
        except Exception:
            logger.exception("Failed to ingest %s", source_file)
            failed += 1

    logger.info("Done. inserted=%d skipped=%d failed=%d total=%d", inserted, skipped, failed, len(records))


if __name__ == "__main__":
    run()
