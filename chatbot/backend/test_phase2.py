"""Phase 2 verification: counts + a test semantic query against ChromaDB.
Run: python -m chatbot.backend.test_phase2
"""
import chromadb

from .config import settings
from .database.mongo_client import get_schemes_collection
from .embeddings.multilingual_e5 import MultilingualE5Embedder

COLLECTION_NAME = "schemes"


def main():
    mongo_count = get_schemes_collection().count_documents({})
    client = chromadb.PersistentClient(path=settings.chroma_persist_path)
    collection = client.get_or_create_collection(COLLECTION_NAME)
    chroma_count = collection.count()

    print(f"MongoDB document count: {mongo_count}")
    print(f"ChromaDB chunk count: {chroma_count}")
    print(f"Expected ChromaDB count (mongo x 4): {mongo_count * 4}")
    print(f"Match: {chroma_count == mongo_count * 4}")

    embedder = MultilingualE5Embedder()
    query_vec = embedder.embed_query(["housing subsidy for poor families"])[0]
    results = collection.query(query_embeddings=[query_vec], n_results=3)

    print("\nTop 3 results for 'housing subsidy for poor families':")
    for i in range(len(results["ids"][0])):
        meta = results["metadatas"][0][i]
        dist = results["distances"][0][i]
        name = meta["scheme_name"].encode("ascii", "replace").decode()
        print(f"  {i+1}. {name} [{meta['section']}] distance={dist:.4f}")


if __name__ == "__main__":
    main()
