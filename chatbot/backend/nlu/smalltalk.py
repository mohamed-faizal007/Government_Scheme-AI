"""Deterministic greetings and thanks (en/hi/ta): matched by rule so they never need an LLM call.
Only a message made up entirely of these words matches; "hi, what schemes are there for farmers?" does not."""
import re

# word -> language it implies (None: English words, answered in the user's language setting)
_GREETINGS = {
    "hi": None, "hii": None, "hello": None, "hey": None, "heyy": None, "hiya": None,
    "namaste": "hi", "namaskar": "hi", "नमस्ते": "hi", "नमस्कार": "hi",
    "vanakkam": "ta", "வணக்கம்": "ta",
}
_THANKS = {
    "thanks": None, "thank": None, "you": None, "thx": None, "very": None, "much": None, "a": None, "lot": None, "so": None,
    "shukriya": "hi", "shukriyaa": "hi", "dhanyavad": "hi", "dhanyavaad": "hi", "धन्यवाद": "hi", "शुक्रिया": "hi",
    "nandri": "ta", "nanri": "ta", "நன்றி": "ta",
}
_THANKS_CORE = frozenset(
    {"thanks", "thank", "thx", "shukriya", "shukriyaa", "dhanyavad", "dhanyavaad", "धन्यवाद", "शुक्रिया", "nandri", "nanri", "நன்றி"}
)
# Letters plus the Devanagari and Tamil blocks (their vowel signs are not \w); punctuation and emoji are ignored.
_WORD_RE = re.compile(r"[ऀ-ॿ]+|[஀-௿]+|[^\W\d_]+")
MAX_WORDS = 5


def match(message: str) -> tuple[str, str | None] | None:
    """("greeting" | "thanks", language implied by the words or None), or None when it is not smalltalk."""
    words = [w.lower() for w in _WORD_RE.findall(message)]
    if not words or len(words) > MAX_WORDS:
        return None
    if any(w in _THANKS_CORE for w in words) and all(w in _THANKS for w in words):
        lang = next((_THANKS[w] for w in words if _THANKS[w]), None)
        return "thanks", lang
    if len(words) == 2 and words[0] == "good" and words[1] in ("morning", "afternoon", "evening"):
        return "greeting", None
    if all(w in _GREETINGS for w in words):
        return "greeting", next((_GREETINGS[w] for w in words if _GREETINGS[w]), None)
    return None
