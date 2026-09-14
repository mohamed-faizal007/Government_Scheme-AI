"""Chunk MongoDB scheme documents into ChromaDB for semantic retrieval.
Idempotent — skips chunk_ids already present. Marks embedding_status='done' in MongoDB.
Run: python -m chatbot.backend.database.load_chroma  (from repo root)
"""
import logging
import re

import chromadb

from ..config import settings
from ..embeddings.multilingual_e5 import MultilingualE5Embedder
from .mongo_client import get_schemes_collection

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

COLLECTION_NAME = "schemes"

STATE_NAMES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa",
    "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala",
    "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland",
    "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal", "Delhi", "Lakshadweep",
    "Puducherry", "Jammu and Kashmir", "Ladakh", "Chandigarh",
]


def extract_state(text: str) -> str:
    for state in STATE_NAMES:
        if state.lower() in text.lower():
            return state
    return ""


def build_chunks(scheme: dict) -> list[dict]:
    scheme_id = str(scheme["_id"])
    scheme_name = scheme.get("metadata", {}).get("scheme_name", "") or ""
    source_file = scheme["source_file"]

    description = scheme.get("overview", {}).get("description", "") or ""
    other_benefits = " ".join(scheme.get("benefits", {}).get("other_benefits", []) or [])
    conditions = " ".join(scheme.get("eligibility", {}).get("conditions", []) or [])
    steps = " ".join(scheme.get("application", {}).get("steps", []) or [])

    sections = {
        "description": description,
        "benefits": other_benefits,
        "eligibility": conditions,
        "application": steps,
    }

    chunks = []
    for section, content in sections.items():
        if section == "benefits":
            text = f"passage: {scheme_name} benefits: {content}"
        elif section == "eligibility":
            text = f"passage: {scheme_name} eligibility: {content}"
        elif section == "application":
            text = f"passage: {scheme_name} application: {content}"
        else:
            text = f"passage: {scheme_name}. {content}"

        chunk_id = f"{source_file}_{section}"
        state = extract_state(conditions) if section == "eligibility" else ""
        chunks.append(
            {
                "chunk_id": chunk_id,
                "text": text,
                "metadata": {
                    "scheme_id": scheme_id,
                    "scheme_name": scheme_name,
                    "source_file": source_file,
                    "section": section,
                    "state": state,
                    "chunk_id": chunk_id,
                },
            }
        )
    return chunks


def run() -> None:
    client = chromadb.PersistentClient(path=settings.chroma_persist_path)
    collection = client.get_or_create_collection(COLLECTION_NAME)
    embedder = MultilingualE5Embedder()
    mongo_collection = get_schemes_collection()

    existing_ids = set(collection.get(include=[])["ids"])

    embedded = 0
    skipped = 0
    failed = 0

    for scheme in mongo_collection.find({}):
        try:
            chunks = build_chunks(scheme)
            new_chunks = [c for c in chunks if c["chunk_id"] not in existing_ids]
            if not new_chunks:
                skipped += len(chunks)
                continue

            vectors = embedder.embed([c["text"] for c in new_chunks])
            collection.add(
                ids=[c["chunk_id"] for c in new_chunks],
                embeddings=vectors,
                documents=[c["text"] for c in new_chunks],
                metadatas=[c["metadata"] for c in new_chunks],
            )
            existing_ids.update(c["chunk_id"] for c in new_chunks)
            embedded += len(new_chunks)
            skipped += len(chunks) - len(new_chunks)

            mongo_collection.update_one(
                {"_id": scheme["_id"]}, {"$set": {"embedding_status": "done"}}
            )
        except Exception:
            logger.exception("Failed to embed scheme %s", scheme.get("source_file"))
            failed += 1

    logger.info("Done. embedded=%d skipped=%d failed=%d", embedded, skipped, failed)


if __name__ == "__main__":
    run()
