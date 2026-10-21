"""One-off: recover real scheme names for schemes whose scheme_name is just their file name
(e.g. "affdf copy"). The name is read, read-only, from the source PDF: the text before
"Are you sure you want to sign out" at the top of page 1. Dry run by default; pass --apply to write.
Run: python -m chatbot.backend.database.fix_filename_schemes [--apply]  (from repo root)

--apply updates scheme_name in MongoDB, then deletes and re-embeds that scheme's ChromaDB chunks
(matched on source_file) using load_chroma.build_chunks. Schemes whose name cannot be recovered,
or whose recovered name duplicates another scheme's name, are left unchanged and reported.
"""
import argparse
import logging
import re
from pathlib import Path

import chromadb
import pymupdf

from ..config import settings
from ..embeddings.multilingual_e5 import MultilingualE5Embedder
from .load_chroma import build_chunks
from .mongo_client import get_schemes_collection
from .scheme_name_utils import clean_scheme_name

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PDF_DIR = Path("dataset/gov_myscheme/unique_pdfs")
CHROMA_COLLECTION = "schemes"
_SIGN_OUT_RE = re.compile(r"are\s+you\s+sure\s+you\s+want\s+to\s+sign\s*out", re.IGNORECASE)


def _stem(source_file: str) -> str:
    return source_file[: -len(".json")] if source_file.endswith(".json") else source_file


def recover_name(source_file: str) -> str | None:
    pdf_path = PDF_DIR / f"{_stem(source_file)}.pdf"
    if not pdf_path.exists():
        return None
    with pymupdf.open(pdf_path) as pdf:
        text = " ".join(pdf[0].get_text().split())
    match = _SIGN_OUT_RE.search(text)
    if not match:
        return None
    name = clean_scheme_name(text[: match.start()]).strip()
    return name or None


def run(apply: bool) -> None:
    mongo = get_schemes_collection()
    chroma = chromadb.PersistentClient(path=settings.chroma_persist_path).get_or_create_collection(
        CHROMA_COLLECTION
    )

    all_names: dict[str, list[str]] = {}
    candidates = []
    for doc in mongo.find({}, {"metadata.scheme_name": 1, "source_file": 1}):
        name = (doc.get("metadata") or {}).get("scheme_name") or ""
        all_names.setdefault(name.casefold(), []).append(doc["source_file"])
        if name.casefold() == _stem(doc["source_file"]).casefold():
            candidates.append((doc["_id"], doc["source_file"], name))

    plan, unrecoverable, duplicates = [], [], []
    new_name_files: dict[str, list[str]] = {}
    for _id, source_file, old in candidates:
        new = recover_name(source_file)
        if not new:
            unrecoverable.append((source_file, old))
            continue
        new_name_files.setdefault(new.casefold(), []).append(source_file)
        plan.append((_id, source_file, old, new))

    final_plan = []
    for _id, source_file, old, new in plan:
        others = [f for f in all_names.get(new.casefold(), []) if f != source_file]
        others += [f for f in new_name_files[new.casefold()] if f != source_file]
        if others:
            duplicates.append((source_file, old, new, others))
        else:
            final_plan.append((_id, source_file, old, new))

    for i, (_id, source_file, old, new) in enumerate(final_plan, 1):
        print(f"{i:>2}. [{source_file}]  {old!r}  ->  {new!r}")
    print(f"\nCandidates (name == file name): {len(candidates)} | to rename: {len(final_plan)} | "
          f"name not recoverable: {len(unrecoverable)} | duplicate of another scheme name: {len(duplicates)}")
    for source_file, old in unrecoverable:
        print(f"  NOT RECOVERABLE: [{source_file}] {old!r}")
    for source_file, old, new, others in duplicates:
        print(f"  DUPLICATE (left unchanged): [{source_file}] {old!r} -> {new!r} already used by {others}")

    old_chunk_ids = {
        source_file: chroma.get(where={"source_file": source_file}, include=[])["ids"]
        for _, source_file, _, _ in final_plan
    }
    matched = sum(len(v) for v in old_chunk_ids.values())
    if not apply:
        print(f"\nDRY RUN (nothing written): {len(final_plan)} MongoDB document(s) to rename, "
              f"{matched} ChromaDB chunk(s) would be re-embedded")
        return

    embedder = MultilingualE5Embedder()
    recreated = 0
    for _id, source_file, old, new in final_plan:
        mongo.update_one({"_id": _id}, {"$set": {"metadata.scheme_name": new}})
        chunks = build_chunks(mongo.find_one({"_id": _id}))
        vectors = embedder.embed([c["text"] for c in chunks])
        if old_chunk_ids[source_file]:
            chroma.delete(ids=old_chunk_ids[source_file])
        chroma.add(
            ids=[c["chunk_id"] for c in chunks],
            embeddings=vectors,
            documents=[c["text"] for c in chunks],
            metadatas=[c["metadata"] for c in chunks],
        )
        recreated += len(chunks)
    print(f"\nAPPLIED: {len(final_plan)} MongoDB document(s) renamed, "
          f"{matched} old chunk(s) deleted, {recreated} chunk(s) re-embedded")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true", help="show changes only (default)")
    group.add_argument("--apply", action="store_true", help="write changes to MongoDB and ChromaDB")
    run(parser.parse_args().apply)
