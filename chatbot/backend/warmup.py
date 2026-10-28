"""Server start-up warm-up: load every slow resource once so the first real query is not slow."""
import logging
import time

logger = logging.getLogger(__name__)


def _timed(label: str, step) -> None:
    start = time.perf_counter()
    try:
        step()
    except Exception:  # noqa: BLE001 - a failed warm-up step must not stop the server; the step retries lazily
        logger.exception("warm-up: %s failed", label)
        return
    logger.info("warm-up: %s ready in %.1fs", label, time.perf_counter() - start)


def warm_up() -> float:
    """Load the embedding model, Chroma, the MongoDB name index and the hi/ta translators, then run one
    dummy retrieval and translation. Returns the total seconds."""
    from .retrieval import retriever
    from .router import scheme_names
    from .translation import translator

    start = time.perf_counter()
    _timed("embedding model", retriever._get_embedder)
    _timed("chroma client", retriever._get_collection)
    _timed("mongodb scheme-name index", scheme_names._load_index)
    _timed("tamil translators", lambda: [translator._get_helsinki(d) for d in ("ta-en", "en-ta")])
    _timed("hindi translators", lambda: (translator.translate("hello", "en", "hi"), translator.translate("नमस्ते", "hi", "en")))
    _timed("dummy retrieval", lambda: retriever.retrieve("schemes for farmers", top_k=1))
    _timed(
        "dummy translation",
        lambda: [translator.translate("This scheme supports farmers.", "en", lang) for lang in ("hi", "ta")],
    )
    total = time.perf_counter() - start
    logger.info("warm-up: finished in %.1fs", total)
    return total
