"""One-off: strip the MyScheme pop-up text from overview.description in MongoDB and keep the
ChromaDB description chunks in step. Dry run by default; pass --apply to write.
Run: python -m chatbot.backend.database.fix_descriptions [--apply]  (from repo root)

--apply (idempotent, safe to re-run):
  - updates overview.description in MongoDB where clean_description() changes it;
  - deletes the `<source_file>_description` chunk of every scheme whose description has no real
    content (see description_utils.has_description_content), so "passage: <name>." alone is never
    embedded; the scheme stays indexed through its benefits, eligibility and application chunks;
  - deletes and re-embeds the description chunk of every scheme whose description changed or whose
    chunk is missing, using load_chroma.build_chunks.
"""
import argparse
import logging

import chromadb

from ..config import settings
from ..embeddings.multilingual_e5 import MultilingualE5Embedder
from .description_utils import clean_description, has_description_content
from .load_chroma import build_chunks
from .mongo_client import get_schemes_collection

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

CHROMA_COLLECTION = "schemes"
EMBED_BATCH = 32


def run(apply: bool) -> None:
    mongo = get_schemes_collection()
    chroma = chromadb.PersistentClient(path=settings.chroma_persist_path).get_or_create_collection(
        CHROMA_COLLECTION
    )
    existing = set(chroma.get(include=[])["ids"])

    mongo_changes = {}  # _id -> new description
    to_delete, to_embed = [], []  # to_embed: (_id, source_file)
    for doc in mongo.find({}, {"overview.description": 1, "source_file": 1}):
        old = (doc.get("overview") or {}).get("description") or ""
        new = clean_description(old)
        changed = new != old
        if changed:
            mongo_changes[doc["_id"]] = new
        chunk_id = f"{doc['source_file']}_description"
        if not has_description_content(new):
            if chunk_id in existing:
                to_delete.append(chunk_id)
        elif changed or chunk_id not in existing:
            to_embed.append((doc["_id"], doc["source_file"]))

    print(
        f"{'APPLY' if apply else 'DRY RUN (nothing written)'}: {len(mongo_changes)} MongoDB description(s) to change, "
        f"{len(to_delete)} content-free description chunk(s) to delete, "
        f"{len(to_embed)} description chunk(s) to (re-)embed"
    )
    if not apply:
        return

    for _id, new in mongo_changes.items():
        mongo.update_one({"_id": _id}, {"$set": {"overview.description": new}})
    if to_delete:
        chroma.delete(ids=to_delete)

    if to_embed:
        embedder = MultilingualE5Embedder()
        for start in range(0, len(to_embed), EMBED_BATCH):
            chunks = []
            for _id, _source_file in to_embed[start:start + EMBED_BATCH]:
                scheme = mongo.find_one({"_id": _id})
                chunks.append(next(c for c in build_chunks(scheme) if c["metadata"]["section"] == "description"))
            vectors = embedder.embed([c["text"] for c in chunks])
            old_ids = [c["chunk_id"] for c in chunks if c["chunk_id"] in existing]
            if old_ids:
                chroma.delete(ids=old_ids)
            chroma.add(
                ids=[c["chunk_id"] for c in chunks],
                embeddings=vectors,
                documents=[c["text"] for c in chunks],
                metadatas=[c["metadata"] for c in chunks],
            )

    print(
        f"APPLIED: {len(mongo_changes)} MongoDB description(s) updated, {len(to_delete)} chunk(s) deleted, "
        f"{len(to_embed)} chunk(s) re-embedded"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true", help="show changes only (default)")
    group.add_argument("--apply", action="store_true", help="write changes to MongoDB and ChromaDB")
    run(parser.parse_args().apply)
