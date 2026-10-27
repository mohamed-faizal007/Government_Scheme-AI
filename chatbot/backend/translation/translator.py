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
PORTAL_URL = "myscheme.gov.in"


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


TYPED_CONFIDENCE = 0.9  # detection confidence needed to override the language pill
TYPED_MIN_WORDS = 3


def resolve_language(message: str, pill: str | None, source: str = "typed") -> str:
    """The language to answer in.

    - source "button" (UI-generated text such as "View details"): the pill, since the user did not
      type that English.
    - typed text of >= 3 words detected with >= 0.9 confidence as en/hi/ta: the detected language,
      even if it disagrees with the pill (the pill itself is never changed).
    - short or uncertain typed text ("ok", a bare scheme name, a number): the pill.
    With no pill, fall back to plain detection.
    """
    if source == "button" and pill:
        return pill
    if len(message.split()) >= TYPED_MIN_WORDS:
        try:
            top = detect_langs(message)[0]
        except (LangDetectException, IndexError):
            top = None
        if top is not None and top.prob >= TYPED_CONFIDENCE and top.lang in SUPPORTED_LANGUAGES:
            return top.lang
    return pill or detect_language(message)


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


_ABBREV_END_RE = re.compile(r"(?:(?:Rs|No|Nos|Dr|Sr|Jr|Mr|Mrs|Ms|vs|etc|approx|Govt|Dept)|[A-Z]|\d|e\.g|i\.e)\.$")


def _split_sentences(line: str) -> list[str]:
    """Sentences of one line. A period after "Rs", "No", a digit or an initial is not a boundary."""
    merged: list[str] = []
    for piece in re.split(r"(?<=[.!?।])\s+", line):
        if merged and _ABBREV_END_RE.search(merged[-1]):
            merged[-1] = f"{merged[-1]} {piece}"
        else:
            merged.append(piece)
    return merged


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
        for line in text.split("\n"):
            if not line.strip():
                out_lines.append(line)
                continue
            # One sentence per model call: given several sentences at once, Marian drops some.
            translated = []
            for sentence in _split_sentences(line):
                for chunk in _split_chunks(sentence):
                    if not chunk.strip():
                        continue
                    batch = tokenizer([prefix + chunk], return_tensors="pt", padding=True, truncation=True)
                    generated = model.generate(**batch, max_new_tokens=512)
                    translated.append(tokenizer.decode(generated[0], skip_special_tokens=True))
            out_lines.append(" ".join(translated))
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


def protect_scheme_names(text: str, schemes: list) -> tuple:
    """Replace scheme names with placeholders before translation."""
    placeholders = {}
    protected_text = text
    for i, name in enumerate(schemes):
        placeholder = f"__SCHEME_{i}__"
        placeholders[placeholder] = name
        protected_text = protected_text.replace(name, placeholder)
    return protected_text, placeholders


def restore_scheme_names(text: str, placeholders: dict) -> str:
    """Restore original scheme names after translation."""
    for placeholder, name in placeholders.items():
        text = text.replace(placeholder, name)
    return text


_HAS_LETTER = re.compile(r"[^\W\d_]")
_LEAD = re.compile(r"^[\s\-–—]*(?:\d+\.\s+)?[\s\-–—]*")
_TRAIL = re.compile(r"(?:\s+\d+\.)?\s*$")


def _translate_segment(segment: str, source_lang: str, target_lang: str) -> str:
    """Translate text between scheme names, line by line.

    Leading list markers ("3. ", dashes) and trailing inline markers (" 3.") are
    lifted out and re-inserted because the model drops or garbles them.
    """
    out_lines = []
    for line in segment.split("\n"):
        if not _HAS_LETTER.search(line):
            out_lines.append(line)
            continue
        lead = _LEAD.match(line).group(0)
        rest = line[len(lead):]
        trail = _TRAIL.search(rest).group(0)
        body = rest[: len(rest) - len(trail)]
        if _HAS_LETTER.search(body):
            body = translate(body, source_lang, target_lang)
        out_lines.append(lead + body + trail)
    return "\n".join(out_lines)


def _translate_around_names(text: str, source_lang: str, target_lang: str, schemes: list) -> str:
    """Translate `text` while keeping `schemes` names (and markdown `**`) verbatim.

    Marian models mangle placeholder tokens (e.g. "__SCHEME_0__" comes back as
    "_SCHEME_ 1_ or ui"), so names are never sent through the model: the text is
    split around them and only the segments between names are translated.
    """
    names = sorted({n for n in schemes if n}, key=len, reverse=True)
    if not names:
        return translate(text, source_lang, target_lang)
    pattern = "(" + "|".join([re.escape(n) for n in names] + [r"\*\*"]) + ")"
    parts = re.split(pattern, text)
    keep = set(names) | {"**"}
    return "".join(
        part if part in keep else _translate_segment(part, source_lang, target_lang) for part in parts
    )


def translate(text: str, source_lang: str, target_lang: str, schemes: list = None) -> str:
    """Translate `text` from `source_lang` to `target_lang`.

    Returns `text` unchanged if source and target match, or if translation
    fails for any reason (network error, rate limiting, etc.) — failures are
    logged but never raised.
    """
    if source_lang == target_lang:
        return text

    if not text or not text.strip():
        return text

    # The portal URL in decline messages gets mangled by Marian ("Mscheme.me.gov."),
    # so it is kept verbatim the same way scheme names are.
    protected = list(schemes) if schemes and target_lang == "ta" else []
    if PORTAL_URL in text:
        protected.append(PORTAL_URL)
    if protected:
        return _translate_around_names(text, source_lang, target_lang, protected)

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
