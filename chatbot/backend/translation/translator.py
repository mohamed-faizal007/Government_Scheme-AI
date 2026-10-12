"""Language detection and output translation.
Run test: python -m chatbot.backend.translation.translator  (from repo root)
"""
import logging
import re

from langdetect import DetectorFactory, detect_langs
from langdetect.lang_detect_exception import LangDetectException

logger = logging.getLogger(__name__)

# Silence HuggingFace model-loading noise.
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

# langdetect's detection is non-deterministic across runs unless seeded.
DetectorFactory.seed = 0

SUPPORTED_LANGUAGES = {"en", "ta", "hi"}
CONFIDENCE_THRESHOLD = 0.7


def detect_language(text: str) -> str:
    """Detect the language of `text`.

    Returns "en", "ta", "hi", or "unknown". Defaults to "en" when detection
    confidence is below CONFIDENCE_THRESHOLD.
    """
    if not text or not text.strip():
        return "en"

    try:
        candidates = detect_langs(text)
    except LangDetectException:
        logger.warning("detect_language: detection failed for input, defaulting to 'en'")
        return "en"

    if not candidates:
        return "en"

    top = candidates[0]
    if top.prob < CONFIDENCE_THRESHOLD:
        logger.info(
            "detect_language: low confidence (%.2f) for '%s', defaulting to 'en'",
            top.prob,
            top.lang,
        )
        return "en"

    if top.lang in SUPPORTED_LANGUAGES:
        return top.lang

    return "unknown"


# Helsinki-NLP Dravidian models cover Tamil (no bilingual ta<->en model exists).
# Loaded lazily and cached: each is a few hundred MB, so never load at import time.
_HELSINKI_MODELS = {
    "ta-en": "Helsinki-NLP/opus-mt-dra-en",
    "en-ta": "Helsinki-NLP/opus-mt-en-dra",
}
_helsinki_cache: dict = {}
_helsinki_failed: set = set()
_MAX_CHUNK_CHARS = 400


def _get_helsinki(direction: str):
    if direction in _helsinki_cache:
        return _helsinki_cache[direction]
    if direction in _helsinki_failed:
        return None
    try:
        from transformers import MarianMTModel, MarianTokenizer

        name = _HELSINKI_MODELS[direction]
        loaded = (MarianTokenizer.from_pretrained(name), MarianMTModel.from_pretrained(name))
        _helsinki_cache[direction] = loaded
        return loaded
    except Exception:
        logger.exception("Helsinki model %s failed to load", _HELSINKI_MODELS[direction])
        _helsinki_failed.add(direction)
        return None


def _split_chunks(text: str) -> list[str]:
    """Split on lines, then sentences, so each piece fits the Marian input limit."""
    chunks = []
    for line in text.split("\n"):
        if len(line) <= _MAX_CHUNK_CHARS:
            chunks.append(line)
            continue
        current = ""
        for sentence in re.split(r"(?<=[.!?।])\s+", line):
            if current and len(current) + len(sentence) + 1 > _MAX_CHUNK_CHARS:
                chunks.append(current)
                current = sentence
            else:
                current = f"{current} {sentence}".strip()
        chunks.append(current)
    return chunks


def _helsinki_translate(text: str, direction: str) -> str | None:
    """Translate with a Helsinki model. Returns None on any failure."""
    loaded = _get_helsinki(direction)
    if loaded is None:
        return None
    tokenizer, model = loaded
    prefix = ">>tam<< " if direction == "en-ta" else ""
    try:
        out_lines = []
        for chunk in _split_chunks(text):
            if not chunk.strip():
                out_lines.append(chunk)
                continue
            batch = tokenizer([prefix + chunk], return_tensors="pt", padding=True, truncation=True)
            generated = model.generate(**batch, max_new_tokens=512)
            out_lines.append(tokenizer.decode(generated[0], skip_special_tokens=True))
        result = "\n".join(out_lines)
    except Exception:
        logger.exception("Helsinki %s translation failed", direction)
        return None
    return result if result.strip() else None


def translate_ta_to_en(text: str) -> str | None:
    """Tamil -> English via local Helsinki opus-mt-dra-en (used for retrieval).

    Returns None if the model is unavailable or fails, so callers can fall back.
    """
    if not text or not text.strip():
        return None
    return _helsinki_translate(text, "ta-en")


def translate(text: str, source_lang: str, target_lang: str) -> str:
    """Translate `text` from `source_lang` to `target_lang`.

    Returns `text` unchanged if source and target match, or if translation
    fails for any reason (network error, rate limiting, etc.) — failures are
    logged but never raised.
    """
    if source_lang == target_lang:
        return text

    if not text or not text.strip():
        return text

    if (source_lang, target_lang) in (("en", "ta"), ("ta", "en")):
        helsinki = _helsinki_translate(text, f"{source_lang}-{target_lang}")
        if helsinki:
            return helsinki
        logger.warning("translate: Helsinki %s->%s unavailable, trying argostranslate", source_lang, target_lang)

    try:
        from argostranslate import translate as argos_translate

        installed_languages = argos_translate.get_installed_languages()
        source = next((lang for lang in installed_languages if lang.code == source_lang), None)
        target = next((lang for lang in installed_languages if lang.code == target_lang), None)

        if source is None or target is None:
            logger.warning(
                "translate: no installed argostranslate language for '%s' -> '%s', "
                "returning original text. Run download_models.py to install packages.",
                source_lang,
                target_lang,
            )
            return text

        translation = source.get_translation(target)
        if translation is None:
            logger.warning(
                "translate: no installed argostranslate package for '%s' -> '%s', "
                "returning original text. Run download_models.py to install packages.",
                source_lang,
                target_lang,
            )
            return text

        translated = translation.translate(text)
    except Exception:
        logger.exception(
            "translate: failed to translate from '%s' to '%s', returning original text",
            source_lang,
            target_lang,
        )
        return text

    if not translated or not translated.strip():
        logger.warning(
            "translate: empty translation result from '%s' to '%s', returning original text",
            source_lang,
            target_lang,
        )
        return text

    return translated


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")

    test_inputs = [
        ("Tamil", "விவசாயிகளுக்கான திட்டங்கள் என்ன?"),
        ("Hindi", "किसानों के लिए क्या योजनाएं हैं?"),
        ("English", "What schemes are available for farmers?"),
    ]

    for label, text in test_inputs:
        lang = detect_language(text)
        print(f"\n=== {label} input ===")
        print(f"Text: {text}")
        print(f"Detected language: {lang}")

    print("\n=== Translation round-trip ===")
    english_answer = "PM-KISAN provides income support to small and marginal farmers."
    for target in ("ta", "hi", "en"):
        result = translate(english_answer, source_lang="en", target_lang=target)
        print(f"en -> {target}: {result}")
