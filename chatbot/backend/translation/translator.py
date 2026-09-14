"""Language detection and output translation.
Run test: python -m chatbot.backend.translation.translator  (from repo root)
"""
import logging

from langdetect import DetectorFactory, detect_langs
from langdetect.lang_detect_exception import LangDetectException

logger = logging.getLogger(__name__)

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
