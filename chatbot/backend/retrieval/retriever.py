"""Hybrid retrieval: regex filter extraction + ChromaDB semantic search + MongoDB hydration.
Run test: python -m chatbot.backend.retrieval.retriever  (from repo root)
"""
import logging
import re
import sys

import chromadb

from ..config import settings
from ..database.load_chroma import STATE_NAMES
from ..database.mongo_client import get_schemes_collection
from ..embeddings.multilingual_e5 import MultilingualE5Embedder

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

COLLECTION_NAME = "schemes"

CATEGORY_PATTERNS = {
    "sc": r"\bsc\b|scheduled caste",
    "st": r"\bst\b|scheduled tribe",
    "obc": r"\bobc\b|other backward class",
    "general": r"\bgeneral category\b",
    "women": r"\bwomen\b|\bwoman\b|\bfemale\b",
    "farmer": r"\bfarmer[s]?\b",
    "student": r"\bstudent[s]?\b",
    "differently abled": r"differently abled|disability|\bpwd\b",
}

BENEFIT_TYPE_PATTERNS = {
    "housing": r"\bhousing\b|\bhouse\b",
    "education": r"\beducation\b|\bscholarship\b",
    "health": r"\bhealth\b|\bmedical\b",
    "agriculture": r"\bagricultur\w*\b|\bcrop\b|\bfarming\b",
    "employment": r"\bemployment\b|\bjob\b|\bself[- ]employ\w*\b",
}

_embedder = None
_collection = None


def _get_embedder() -> MultilingualE5Embedder:
    global _embedder
    if _embedder is None:
        _embedder = MultilingualE5Embedder()
    return _embedder


def _get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=settings.chroma_persist_path)
        _collection = client.get_or_create_collection(COLLECTION_NAME)
    return _collection


def extract_filters(query: str) -> dict:
    filters = {}

    for state in STATE_NAMES:
        if state.lower() in query.lower():
            filters["state"] = state
            break

    for category, pattern in CATEGORY_PATTERNS.items():
        if re.search(pattern, query, re.IGNORECASE):
            filters["category"] = category
            break

    for benefit_type, pattern in BENEFIT_TYPE_PATTERNS.items():
        if re.search(pattern, query, re.IGNORECASE):
            filters["benefit_type"] = benefit_type
            break

    return filters


def retrieve(query: str, filters: dict = None, top_k: int = 5) -> list[dict]:
    extracted = extract_filters(query)
    if filters:
        extracted.update({k: v for k, v in filters.items() if v})
    filters = extracted

    embedder = _get_embedder()
    query_vector = embedder.embed([f"query: {query}"])[0]

    collection = _get_collection()

    # Only "state" is indexed as ChromaDB metadata (see load_chroma.py) — category
    # and benefit_type are extracted for logging/downstream use but not enforced
    # as a hard filter here since they are not stored per-chunk.
    where = {"state": filters["state"]} if filters.get("state") else None

    fetch_n = top_k * 2
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=fetch_n,
        where=where,
        include=["metadatas", "distances"],
    )

    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    if not metadatas and where is not None:
        # Fall back to an unfiltered search if the state filter over-constrained results.
        results = collection.query(
            query_embeddings=[query_vector],
            n_results=fetch_n,
            include=["metadatas", "distances"],
        )
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

    mongo_collection = get_schemes_collection()
    seen_scheme_ids = set()
    hits = []

    from bson import ObjectId

    for metadata, distance in zip(metadatas, distances):
        scheme_id = metadata["scheme_id"]
        if scheme_id in seen_scheme_ids:
            continue
        seen_scheme_ids.add(scheme_id)

        doc = mongo_collection.find_one({"_id": ObjectId(scheme_id)})
        if not doc:
            continue
        doc["_id"] = str(doc["_id"])

        hits.append(
            {
                "scheme": doc,
                "scheme_name": metadata["scheme_name"],
                "section": metadata["section"],
                "source_file": metadata["source_file"],
                "score": 1 - distance,
            }
        )

        if len(hits) >= top_k:
            break

    return hits


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    test_queries = [
        "schemes for farmers in Tamil Nadu",
        "housing subsidy for SC category",
        "education scholarship below 2 lakh income",
        "விவசாயிகளுக்கான திட்டங்கள்",
        "किसानों के लिए योजनाएं",
    ]

    for i, q in enumerate(test_queries, start=1):
        print(f"\n=== Query {i}: {q} ===")
        filters = extract_filters(q)
        print(f"Extracted filters: {filters}")
        results = retrieve(q, top_k=5)
        if not results:
            print("No results.")
            continue
        for r in results:
            print(f"  [{r['score']:.4f}] {r['scheme_name']!r} (section={r['section']}, file={r['source_file']})")
