"""One-off: strip UI-text suffixes from scheme_name in MongoDB and ChromaDB metadata.
Dry run by default; pass --apply to write.
Run: python -m chatbot.backend.database.fix_scheme_names [--apply]  (from repo root)

--apply updates scheme_name in MongoDB, then deletes and re-embeds only the affected schemes'
ChromaDB chunks (matched on source_file) using load_chroma.build_chunks.
"""
import argparse
import logging

import chromadb

from ..config import settings
from ..embeddings.multilingual_e5 import MultilingualE5Embedder
from .load_chroma import build_chunks
from .mongo_client import get_schemes_collection
from .scheme_name_utils import clean_scheme_name

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

CHROMA_COLLECTION = "schemes"


def run(apply: bool) -> None:
    mongo = get_schemes_collection()
    chroma = chromadb.PersistentClient(path=settings.chroma_persist_path).get_or_create_collection(
        CHROMA_COLLECTION
    )

    changes = []
    for doc in mongo.find({}, {"metadata.scheme_name": 1, "source_file": 1}):
        old = (doc.get("metadata") or {}).get("scheme_name")
        if not old:
            continue
        new = clean_scheme_name(old)
        if new != old:
            changes.append((doc["_id"], doc.get("source_file"), old, new))

    embedder = MultilingualE5Embedder() if apply and changes else None
    chroma_matched = 0
    chroma_recreated = 0
    for i, (_id, source_file, old, new) in enumerate(changes, 1):
        print(f"{i}. [{source_file}]\n   before: {old!r}\n   after:  {new!r}")

        old_ids = chroma.get(where={"source_file": source_file}, include=[])["ids"]
        chroma_matched += len(old_ids)
        if not apply:
            continue

        mongo.update_one({"_id": _id}, {"$set": {"metadata.scheme_name": new}})
        # Re-embed: drop only this scheme's chunks, rebuild them from the cleaned Mongo doc.
        scheme = mongo.find_one({"_id": _id})
        chunks = build_chunks(scheme)
        vectors = embedder.embed([c["text"] for c in chunks])
        if old_ids:
            chroma.delete(ids=old_ids)
        chroma.add(
            ids=[c["chunk_id"] for c in chunks],
            embeddings=vectors,
            documents=[c["text"] for c in chunks],
            metadatas=[c["metadata"] for c in chunks],
        )
        chroma_recreated += len(chunks)

    if apply:
        print(
            f"\nAPPLIED: {len(changes)} MongoDB document(s) updated, "
            f"{chroma_matched} old chunk(s) deleted, {chroma_recreated} chunk(s) re-embedded"
        )
    else:
        print(
            f"\nDRY RUN (nothing written): {len(changes)} MongoDB document(s) to change, "
            f"{chroma_matched} ChromaDB chunk(s) would be re-embedded"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true", help="show changes only (default)")
    group.add_argument("--apply", action="store_true", help="write changes to MongoDB and ChromaDB")
    run(parser.parse_args().apply)
