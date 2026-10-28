"""Presentation layer for eligibility answers: what to show, in which order, in en/hi/ta.

The three-valued evaluation lives in rules_engine and is not touched here. This module only decides how
its output is worded and which fragments are worth showing. All fixed phrases are templates, so scheme
names are inserted verbatim and never pass through machine translation.
Run test: python -m pytest chatbot/evaluation/test_eligibility_presentation_offline.py  (from repo root)
"""
import re

from ..database.load_chroma import STATE_NAMES
from .rules_engine import _MAX_REASON_LEN, _is_junk
from .user_profile import UserProfile

MAX_SCHEMES = 5
MAX_CONDITIONS = 3
FILTER_MAX_LEN = 160
SHORTEN_TO = _MAX_REASON_LEN
# The engine cuts long conditions to _MAX_REASON_LEN chars plus "..."; that tail is not source truncation.
_ENGINE_CUT_LEN = _MAX_REASON_LEN + 3

PROFILE_FIELDS = ["age", "gender", "state", "income_annual", "category", "occupation"]
MISSING_CANDIDATES = ["age", "state", "income_annual", "category", "gender"]

# ---------------------------------------------------------------------------
# Topics
# ---------------------------------------------------------------------------
# key -> (chip words in en/hi/ta, regex a user reply is matched with, regex a scheme's own labels are matched with)
TOPICS = {
    "agriculture": {
        "label": {"en": "Farming", "hi": "खेती", "ta": "விவசாயம்"},
        "word": "agriculture",
        "reply": r"farm|agricultur|crop|kisan|खेती|कृषि|किसान|விவசாய",
        "scheme": r"agricultur|\bfarm|\bcrop|kisan|irrigation|horticultur|livestock|dairy|fisher|\bseed",
    },
    "education": {
        "label": {"en": "Education", "hi": "शिक्षा", "ta": "கல்வி"},
        "word": "education",
        "reply": r"educat|scholarship|student|school|college|शिक्षा|छात्र|கல்வி|மாணவ",
        "scheme": r"educat|scholarship|student|school|college|tuition|fellowship",
    },
    "housing": {
        "label": {"en": "Housing", "hi": "आवास", "ta": "வீட்டுவசதி"},
        "word": "housing",
        "reply": r"housing|\bhouse\b|\bhome\b|आवास|घर|வீடு|வீட்டு",
        "scheme": r"housing|\bhouse|awas|\bhome\b|shelter|accommodation",
    },
    "business": {
        "label": {"en": "Business", "hi": "व्यापार", "ta": "தொழில்"},
        "word": "business",
        "reply": r"business|entrepreneur|startup|self[- ]?employ|msme|व्यापार|कारोबार|தொழில்",
        "scheme": r"business|entrepreneur|enterprise|startup|start-up|msme|self[- ]?employ|artisan|industr",
    },
    "health": {
        "label": {"en": "Health", "hi": "स्वास्थ्य", "ta": "சுகாதாரம்"},
        "word": "health",
        "reply": r"health|medical|hospital|स्वास्थ्य|சுகாதார|மருத்துவ",
        "scheme": r"health|medical|hospital|treatment|arogya|ayushman|insurance",
    },
    "pension": {
        "label": {"en": "Pension", "hi": "पेंशन", "ta": "ஓய்வூதியம்"},
        "word": "pension",
        "reply": r"pension|old age|retire|पेंशन|ஓய்வூதிய",
        "scheme": r"pension|old age|senior citizen|retire|elderly",
    },
    "employment": {
        "label": {"en": "Employment", "hi": "रोज़गार", "ta": "வேலைவாய்ப்பு"},
        "word": "employment",
        "reply": r"employment|\bjobs?\b|रोज़गार|रोजगार|வேலை",
        "scheme": r"employment|\bjob|skill|unemploy|livelihood|training",
    },
}
CHIP_ORDER = ["agriculture", "education", "housing", "business", "health", "pension"]

# occupation / profile hint -> topic
_OCCUPATION_HINTS = [
    (r"farm|agricultur|cultivat|kisan|ryot|खेती|किसान|விவசாய", "agriculture"),
    (r"student|pupil|scholar|छात्र|மாணவ", "education"),
    (r"unemploy|job[- ]?seek", "employment"),
    (r"entrepreneur|business|shop|self[- ]?employ|artisan|weaver|vendor", "business"),
    (r"retired|pensioner|senior citizen", "pension"),
]


def topic_hint(profile: UserProfile) -> str | None:
    """The topic implied by the profile (occupation, student flag), or None."""
    occupation = (profile.occupation or "").lower()
    for pattern, topic in _OCCUPATION_HINTS:
        if occupation and re.search(pattern, occupation):
            return topic
    if profile.is_student:
        return "education"
    return None


def parse_topic_reply(text: str) -> str | None:
    """Read a reply to the "which area?" question (a chip's value or free text)."""
    for topic, spec in TOPICS.items():
        if re.search(spec["reply"], text, re.IGNORECASE):
            return topic
    return None


def topic_query(topic: str) -> str:
    return f"{TOPICS[topic]['word']} schemes"


def _scheme_labels(scheme: dict) -> str:
    meta = scheme.get("metadata", {}) or {}
    search = scheme.get("search_metadata", {}) or {}
    parts = [meta.get("scheme_name"), meta.get("scheme_type"), meta.get("category"), meta.get("implementing_department")]
    parts += list(search.get("tags") or []) + list(search.get("keywords") or [])
    return " ".join(str(p) for p in parts if p)


def scheme_matches_topic(scheme: dict, topic: str) -> bool:
    return bool(re.search(TOPICS[topic]["scheme"], _scheme_labels(scheme), re.IGNORECASE))


_NOT_ELIGIBLE_ASK = re.compile(
    r"not\s+(?:eligible|qualif)|ineligible|(?:am|are)n'?t\s+eligible|don'?t\s+qualify|do\s+not\s+qualify", re.IGNORECASE
)


def wants_not_eligible(text: str) -> bool:
    """True when the user asks to see the schemes they are NOT eligible for."""
    return bool(text and _NOT_ELIGIBLE_ASK.search(text) and re.search(r"\b(?:show|list|see|which|what)\b", text, re.IGNORECASE))


# ---------------------------------------------------------------------------
# Unverified-condition filter
# ---------------------------------------------------------------------------
_BOILERPLATE_START = re.compile(r"^(?:note|step|obligation|what|how|whether|can)\b", re.IGNORECASE)
_LEADING_MARK = re.compile(r"^[\s\-•*\d.)(:]+")


def _looks_like_boilerplate(text: str) -> bool:
    body = _LEADING_MARK.sub("", text.strip())
    if _BOILERPLATE_START.match(body) or body.rstrip().endswith("?"):
        return True
    if "..." in text:
        # Only the engine's own tail (exactly _MAX_REASON_LEN chars then "...") is a legitimate cut.
        engine_cut = len(text) == _ENGINE_CUT_LEN and text.endswith("...") and "..." not in text[:-3]
        return not engine_cut
    return False


def clean_condition(text: str) -> str | None:
    """A condition worth showing, shortened if long, or None for FAQ/boilerplate fragments."""
    text = " ".join((text or "").split())
    if not text or _is_junk(text) or _looks_like_boilerplate(text):
        return None
    if len(text) > FILTER_MAX_LEN:
        return text[:SHORTEN_TO].rstrip() + "..."
    return text


def filter_conditions(conditions: list[str]) -> list[str]:
    seen, out = set(), []
    for raw in conditions:
        cleaned = clean_condition(raw)
        if cleaned and cleaned.lower() not in seen:
            seen.add(cleaned.lower())
            out.append(cleaned)
    return out


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------
_FIELD_IN_CONDITION = {
    "age": re.compile(r"\bage\b|\byears?\b", re.IGNORECASE),
    "income_annual": re.compile(r"income|\bbpl\b|\bapl\b", re.IGNORECASE),
    "category": re.compile(r"\bsc\b|\bst\b|\bobc\b|caste|tribe|category|backward|minorit", re.IGNORECASE),
    "gender": re.compile(r"\bwom[ae]n\b|female|\bmale\b|gender|widow|\bgirl", re.IGNORECASE),
}
_STATE_IN_CONDITION = re.compile(r"resident|domicile|\bstate\b|" + "|".join(re.escape(s) for s in STATE_NAMES), re.IGNORECASE)


def missing_fields(profile: UserProfile, conditions: list[str]) -> list[str]:
    """Empty profile fields that the scheme's unchecked conditions actually talk about."""
    text = " ".join(conditions)
    missing = []
    for field in MISSING_CANDIDATES:
        if getattr(profile, field) is not None:
            continue
        pattern = _STATE_IN_CONDITION if field == "state" else _FIELD_IN_CONDITION[field]
        if pattern.search(text):
            missing.append(field)
    return missing


def assess(result: dict, profile: UserProfile) -> dict:
    """status is "eligible", "may" or "not"; `conditions` are the unverified ones worth showing."""
    conditions = filter_conditions(result["unverifiable_conditions"])
    missing = missing_fields(profile, conditions)
    if not result["eligible"]:
        status = "not"
    elif conditions or missing or not result["reasons"]:
        status = "may"  # something unchecked, or nothing was actually checked
    else:
        status = "eligible"
    return {"status": status, "conditions": conditions, "missing": missing}


# Splits after ". " but not after abbreviations such as "Rs." or "No.".
_SENTENCE_END = re.compile(r"(?<![Rr]s)(?<!No)(?<!Dr)(?<!Sh)(?<=[.!])\s+(?=[A-Z])")


_BENEFIT_LABEL = re.compile(r"^\s*pattern of assistance\s*:\s*", re.IGNORECASE)


def benefit_line(scheme: dict) -> str | None:
    benefits = scheme.get("benefits", {}) or {}
    candidates = [benefits.get("financial_assistance")] + list(benefits.get("other_benefits") or [])
    for candidate in candidates:
        if isinstance(candidate, str):
            candidate = _BENEFIT_LABEL.sub("", candidate)  # "Pattern of Assistance:Rs. 5,000..." -> "Rs. 5,000..."
        cleaned = clean_condition(candidate) if isinstance(candidate, str) else None
        if cleaned:
            first = _SENTENCE_END.split(cleaned, maxsplit=1)[0]
            return first if len(first) <= SHORTEN_TO else first[:SHORTEN_TO].rstrip() + "..."
    return None


# ---------------------------------------------------------------------------
# Templates (fixed text, en/hi/ta)
# ---------------------------------------------------------------------------
FIELD_LABELS = {
    "en": {"age": "age", "gender": "gender", "state": "state", "income_annual": "annual income",
           "category": "category", "occupation": "occupation"},
    "hi": {"age": "आयु", "gender": "लिंग", "state": "राज्य", "income_annual": "वार्षिक आय",
           "category": "श्रेणी", "occupation": "व्यवसाय"},
    "ta": {"age": "வயது", "gender": "பாலினம்", "state": "மாநிலம்", "income_annual": "ஆண்டு வருமானம்",
           "category": "பிரிவு", "occupation": "தொழில்"},
}

T = {
    "en": {
        "eligible": "You appear to be eligible.",
        "may": "You may be eligible.",
        "not": "You do not appear to be eligible.",
        "missing": "Missing details: {fields}. Tell me these and I will check again.",
        "unchecked": "Some conditions could not be checked automatically:",
        "more": "{n} more conditions could not be checked automatically; see the scheme page.",
        "none_fit": "I could not find a scheme you are eligible for among the closest matches. These were checked:",
        "hidden": "I left out {n} scheme(s) you do not appear to be eligible for. Say \"show schemes I'm not eligible for\" to see them.",
        "intro": "Here is what I found for your profile:",
        "hint": "Using your occupation ({occupation}), I searched {topic} schemes.",
        "no_state": "I found no schemes specific to {state} in my data, so these are central (not state-specific) schemes only.",
        "no_match": "I could not find any {topic} schemes to check. Please try another area or visit myscheme.gov.in.",
        "no_result": "I couldn't find a matching scheme to check eligibility against. Please check myscheme.gov.in.",
        "ask_topic": "Which area are you interested in? (farming, education, housing, business, health, pension...)",
        "read": "I read these from your document: {fields}.",
        "confirm": "Please confirm: {fields}.",
        "not_found": "Not found in the document: {fields}.",
        "none_read": "I couldn't confidently read any fields from that document.",
        "profile": "Your current profile: {profile}.",
        "carry": "Details from earlier in this chat are kept. Start a new conversation to clear them.",
    },
    "hi": {
        "eligible": "आप पात्र प्रतीत होते हैं।",
        "may": "आप पात्र हो सकते हैं।",
        "not": "आप पात्र प्रतीत नहीं होते हैं।",
        "missing": "अधूरी जानकारी: {fields}। ये बताइए, मैं फिर से जांचूंगा।",
        "unchecked": "कुछ शर्तें अपने आप जांची नहीं जा सकीं:",
        "more": "{n} और शर्तें अपने आप जांची नहीं जा सकीं; योजना का पेज देखें।",
        "none_fit": "सबसे मिलती-जुलती योजनाओं में कोई ऐसी नहीं मिली जिसके लिए आप पात्र हों। ये जांची गईं:",
        "hidden": "मैंने {n} ऐसी योजना छोड़ दी जिनके लिए आप पात्र प्रतीत नहीं होते। देखने के लिए \"show schemes I'm not eligible for\" लिखें।",
        "intro": "आपकी प्रोफ़ाइल के लिए ये मिला:",
        "hint": "आपके व्यवसाय ({occupation}) के आधार पर मैंने {topic} योजनाएं खोजीं।",
        "no_state": "मेरे डेटा में {state} की अपनी कोई योजना नहीं मिली, इसलिए ये केवल केंद्रीय (राज्य-विशेष नहीं) योजनाएं हैं।",
        "no_match": "जांचने के लिए {topic} की कोई योजना नहीं मिली। कृपया कोई और क्षेत्र चुनें या myscheme.gov.in देखें।",
        "no_result": "पात्रता जांचने के लिए कोई मेल खाती योजना नहीं मिली। कृपया myscheme.gov.in देखें।",
        "ask_topic": "आप किस क्षेत्र में रुचि रखते हैं? (खेती, शिक्षा, आवास, व्यापार, स्वास्थ्य, पेंशन...)",
        "read": "मैंने आपके दस्तावेज़ से ये पढ़ा: {fields}।",
        "confirm": "कृपया पुष्टि करें: {fields}।",
        "not_found": "दस्तावेज़ में नहीं मिला: {fields}।",
        "none_read": "मैं उस दस्तावेज़ से कोई जानकारी भरोसे के साथ नहीं पढ़ सका।",
        "profile": "आपकी मौजूदा प्रोफ़ाइल: {profile}।",
        "carry": "इस चैट की पहले की जानकारी रखी गई है। हटाने के लिए नई बातचीत शुरू करें।",
    },
    "ta": {
        "eligible": "நீங்கள் தகுதியானவராகத் தெரிகிறது.",
        "may": "நீங்கள் தகுதியானவராக இருக்கலாம்.",
        "not": "நீங்கள் தகுதியானவராகத் தெரியவில்லை.",
        "missing": "இல்லாத விவரங்கள்: {fields}. இவற்றைச் சொன்னால் மீண்டும் சரிபார்க்கிறேன்.",
        "unchecked": "சில நிபந்தனைகளைத் தானாகச் சரிபார்க்க முடியவில்லை:",
        "more": "மேலும் {n} நிபந்தனைகளைத் தானாகச் சரிபார்க்க முடியவில்லை; திட்டப் பக்கத்தைப் பாருங்கள்.",
        "none_fit": "மிக நெருங்கிய திட்டங்களில் நீங்கள் தகுதியானவர் எதுவும் கிடைக்கவில்லை. இவை சரிபார்க்கப்பட்டன:",
        "hidden": "நீங்கள் தகுதியற்ற {n} திட்டம்(ங்கள்) தவிர்க்கப்பட்டன. பார்க்க \"show schemes I'm not eligible for\" என்று எழுதுங்கள்.",
        "intro": "உங்கள் சுயவிவரத்திற்கு கிடைத்தவை:",
        "hint": "உங்கள் தொழிலின் ({occupation}) அடிப்படையில் {topic} திட்டங்களைத் தேடினேன்.",
        "no_state": "என் தரவில் {state} மாநிலத்துக்கே உரிய திட்டங்கள் எதுவும் கிடைக்கவில்லை; எனவே இவை மத்திய (மாநிலம் சார்ந்ததல்லாத) திட்டங்கள் மட்டுமே.",
        "no_match": "சரிபார்க்க {topic} திட்டங்கள் எதுவும் கிடைக்கவில்லை. வேறு துறையைத் தேர்வு செய்யுங்கள் அல்லது myscheme.gov.in பாருங்கள்.",
        "no_result": "தகுதியைச் சரிபார்க்க பொருந்தும் திட்டம் கிடைக்கவில்லை. myscheme.gov.in தளத்தைப் பாருங்கள்.",
        "ask_topic": "எந்தத் துறையில் ஆர்வம் உள்ளது? (விவசாயம், கல்வி, வீட்டுவசதி, தொழில், சுகாதாரம், ஓய்வூதியம்...)",
        "read": "உங்கள் ஆவணத்தில் இருந்து இவற்றைப் படித்தேன்: {fields}.",
        "confirm": "தயவுசெய்து உறுதிப்படுத்துங்கள்: {fields}.",
        "not_found": "ஆவணத்தில் கிடைக்காதவை: {fields}.",
        "none_read": "அந்த ஆவணத்தில் இருந்து எந்த விவரத்தையும் உறுதியாகப் படிக்க முடியவில்லை.",
        "profile": "உங்கள் தற்போதைய சுயவிவரம்: {profile}.",
        "carry": "இந்த அரட்டையில் முன்பு தந்த விவரங்கள் வைக்கப்பட்டுள்ளன. அழிக்க புதிய உரையாடலைத் தொடங்குங்கள்.",
    },
}


def _t(language: str) -> dict:
    return T.get(language, T["en"])


def _labels(language: str) -> dict:
    return FIELD_LABELS.get(language, FIELD_LABELS["en"])


def _topic_label(topic: str, language: str) -> str:
    return TOPICS[topic]["label"].get(language, TOPICS[topic]["label"]["en"])


def topic_question(language: str) -> tuple[str, list[dict]]:
    """The "which area?" prompt and its quick-reply chips (label shown, English value sent back)."""
    chips = [{"label": _topic_label(t, language), "value": TOPICS[t]["label"]["en"].lower()} for t in CHIP_ORDER]
    return _t(language)["ask_topic"], chips


def hint_note(occupation: str, topic: str, language: str) -> str:
    return _t(language)["hint"].format(occupation=occupation, topic=_topic_label(topic, language).lower())


def no_state_note(state: str, language: str) -> str:
    return _t(language)["no_state"].format(state=state)


def no_match_text(topic: str, language: str) -> str:
    return _t(language)["no_match"].format(topic=_topic_label(topic, language).lower())


def no_result_text(language: str) -> str:
    return _t(language)["no_result"]


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def select_entries(entries: list[dict], show_not: bool) -> tuple[list[dict], int, bool]:
    """(entries to show, how many 'not eligible' were hidden, True when none were eligible/may)."""
    good = [e for e in entries if e["status"] != "not"]
    bad = [e for e in entries if e["status"] == "not"]
    # eligible first, then fewest unverified conditions; the sort is stable, so retrieval order breaks remaining ties
    good.sort(key=lambda e: (0 if e["status"] == "eligible" else 1, len(e["conditions"])))
    if show_not:
        return (good + bad)[:MAX_SCHEMES], 0, False
    if good:
        return good[:MAX_SCHEMES], len(bad), False
    return bad[:MAX_SCHEMES], 0, True


def _render_entry(index: int, entry: dict, language: str) -> str:
    t, labels = _t(language), _labels(language)
    head = f"{index}. **{entry['scheme_name']}**" + (f" - {entry['benefit']}" if entry.get("benefit") else "")
    lines = [head, t[entry["status"]]]
    if entry["status"] == "not":
        lines[-1] += " (" + "; ".join(entry["failed"][:MAX_CONDITIONS]) + ")"
        return "\n".join(lines)
    if entry["missing"]:
        lines.append(t["missing"].format(fields=", ".join(labels[f] for f in entry["missing"])))
    shown = entry["conditions"][:MAX_CONDITIONS]
    if shown:
        lines.append(t["unchecked"])
        lines += [f"- {c}" for c in shown]
    extra = len(entry["conditions"]) - len(shown)
    if extra > 0:
        lines.append(t["more"].format(n=extra))
    return "\n".join(lines)


def render_answer(entries: list[dict], language: str, show_not: bool = False, note: str | None = None) -> tuple[str, list[dict]]:
    """The eligibility answer text and the entries that were shown."""
    t = _t(language)
    shown, hidden, none_fit = select_entries(entries, show_not)
    blocks = []
    if note:
        blocks.append(note)
    blocks.append(t["none_fit"] if none_fit else t["intro"])
    blocks += [_render_entry(i, e, language) for i, e in enumerate(shown, 1)]
    if hidden:
        blocks.append(t["hidden"].format(n=hidden))
    return "\n\n".join(blocks), shown


def make_entry(hit: dict, result: dict, profile: UserProfile) -> dict:
    verdict = assess(result, profile)
    return {
        "scheme_name": hit["scheme_name"],
        "hit": hit,
        "benefit": benefit_line(hit["scheme"]),
        "status": verdict["status"],
        "conditions": verdict["conditions"],
        "missing": verdict["missing"],
        "failed": [f for f in result["failed_conditions"]] or ["some conditions are not met"],
        "eligible": result["eligible"],
    }


# ---------------------------------------------------------------------------
# Document-upload confirmation
# ---------------------------------------------------------------------------
def _format_value(field: str, value) -> str:
    if field == "income_annual":
        return f"₹{int(value):,}" if float(value).is_integer() else f"₹{value:,}"
    if field == "category":
        return str(value).upper() if str(value).lower() in ("sc", "st", "obc") else str(value).title()
    return str(value).title() if field in ("gender", "state") else str(value)


def profile_summary(profile: UserProfile, language: str = "en") -> str:
    labels = _labels(language)
    parts = [f"{labels[f]}: {_format_value(f, getattr(profile, f))}" for f in PROFILE_FIELDS if getattr(profile, f) is not None]
    return "; ".join(parts)


def upload_message(fill_result: dict, language: str = "en") -> str:
    """The confirmation shown after a document upload: what was read, what to confirm, the whole profile."""
    t, labels = _t(language), _labels(language)
    profile: UserProfile = fill_result["updated_profile"]
    read = fill_result["high_confidence_fills"] + fill_result["needs_confirmation"]
    parts = []
    if read:
        parts.append(t["read"].format(fields=", ".join(f"{labels[f]}: {_format_value(f, getattr(profile, f))}" for f in read)))
        if fill_result["needs_confirmation"]:
            parts.append(t["confirm"].format(fields=", ".join(labels[f] for f in fill_result["needs_confirmation"])))
        if fill_result["failed_fields"]:
            parts.append(t["not_found"].format(fields=", ".join(labels[f] for f in fill_result["failed_fields"])))
    else:
        parts.append(t["none_read"])
    summary = profile_summary(profile, language)
    if summary:
        parts.append(t["profile"].format(profile=summary))
        parts.append(t["carry"])
    return " ".join(parts)
