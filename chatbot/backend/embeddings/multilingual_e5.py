from sentence_transformers import SentenceTransformer

from .base import BaseEmbedder

MODEL_NAME = "intfloat/multilingual-e5-small"

_model = SentenceTransformer(MODEL_NAME)


class MultilingualE5Embedder(BaseEmbedder):
    """intfloat/multilingual-e5-small requires a task prefix on every input:
    'query: ' for search queries, 'passage: ' for stored documents. Mixing these
    up silently degrades retrieval quality, so this class never accepts raw text —
    only pre-fixed text via embed(), plus explicit embed_query/embed_passage helpers."""

    def __init__(self):
        self.model = _model

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, normalize_embeddings=True).tolist()

    def embed_query(self, texts: list[str]) -> list[list[float]]:
        return self.embed([f"query: {t}" for t in texts])

    def embed_passage(self, texts: list[str]) -> list[list[float]]:
        return self.embed([f"passage: {t}" for t in texts])
