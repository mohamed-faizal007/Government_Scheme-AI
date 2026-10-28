"""Deterministic keyword/regex intent router — no LLM call, so it's fast and reproducible.
Run test: python -m chatbot.backend.router.intent_classifier  (from repo root)
"""
import re

from ..database.load_chroma import STATE_NAMES
from .scheme_names import find_schemes_in

# Questions about a scheme's own rules ("who can apply", "how can I apply"). They would otherwise be
# swallowed by the first-person eligibility patterns ("can i apply"), so they are checked first.
SCHEME_DETAIL_PATTERNS = [
    r"\bwho\s+(?:all\s+)?(?:can|could|may)\s+apply\b", r"\bwho\s+(?:is|are)\s+eligible\b",
    r"\bhow\s+(?:can|do|should|to)\s+(?:i\s+)?apply\b",
    r"\btell\s+me\s+more\b", r"\bmore\s+(?:details?|info(?:rmation)?)\b",
    r"\bdetails?\s+(?:of|about|on|for)\b", r"\bgive\s+me\s+(?:the\s+)?details?\b",
    r"\bdocuments?\s+(?:needed|required|necessary)\b", r"\beligibility\s+criteria\b",
    r"\bapplication\s+(?:process|procedure)\b",
    # Romanized Hindi
    r"\bkaun\b.*\b(?:apply|avedan|aavedan)\b", r"\bkaise\s+(?:apply|avedan|aavedan)\b",
    r"\baur\s+(?:batao|bataiye|jaankari|jankari)\b", r"\bdastavez\b",
]

# Native-script versions. "कौन आवेदन कर सकता है" (who can apply) must not hit the first-person
# eligibility pattern "आवेदन कर सकता".
NATIVE_SCHEME_DETAIL_PATTERNS = [
    r"कौन.*(?:आवेदन|पात्र)", r"और\s*(?:बता|जानकारी)", r"अधिक\s*जानकारी", r"विवरण", r"ब्यौरा",
    r"कैसे\s*आवेदन", r"आवश्यक\s*दस्तावेज",
    r"யார்.*(?:விண்ணப்பிக்க|தகுதி)", r"மேலும்\s*(?:சொல்|தெரிந்து|விவரம்|தகவல்)", r"விவரங்கள்|விவரம்",
    r"எப்படி\s*விண்ணப்பிக்க", r"தேவையான\s*ஆவணங்கள்",
]

ELIGIBILITY_PATTERNS = [
    r"am i eligible", r"do i qualify", r"can i apply", r"check eligibility", r"eligible for",
]

DOCUMENT_PATTERNS = [
    r"\bupload\b", r"verify document", r"check my document", r"my certificate",
]

COMPARISON_PATTERNS = [
    r"\bcompare\b", r"difference between", r"which is better", r"\bvs\b",
]

_ROMAN_HINDI_SCHEME_WORDS = (
    r"yojana|yojna|scheme|labh|subsidy|pension|sahayata|scholarship|bima|anudan|chhatravritti"
)

SCHEME_SEARCH_PATTERNS = [
    r"what is", r"tell me about", r"how to apply", r"schemes for", r"benefits of",
    r"documents required", r"schemes? (?:are|is)?\s*available", r"available for",
    r"\bexplain\b", r"\bwhat\s+(?:documents|identity|proof|benefits)\b",
    r"\bdocuments?\b.*\b(?:required|needed|need)\b", r"\b(?:need|require)\b.*\bdocuments?\b",
    r"how much\b", r"how do i (?:claim|get)\b", r"what does\b.*\bprovide\b",
    r"what benefits\b", r"\bwhich scheme\b",
    # Typical English renderings of Hindi/Tamil scheme-search questions.
    r"\bwhat schemes?\b", r"\bwhich schemes?\b", r"\bgovernment schemes?\b",
    r"\bschemes? for (?:farmers?|women|students?)\b", r"\bwhat are the schemes?\b",
    r"\btell me (?:the |about )?schemes?\b", r"\bavailable schemes?\b",
    # Romanized Hindi. The generic phrases only count together with a scheme word, so
    # "aaj mausam kya hai" and "mujhe kuch batao" stay out of scope.
    r"\b(?:yojana|yojna)\b",
    rf"(?=.*\b(?:{_ROMAN_HINDI_SCHEME_WORDS})\b).*\b(?:ke\s+baa?re\s+mein|bataiye|batao|kya\s+hai)\b",
]

# Native-script keywords, checked before any translation. Substring match
# (no \b) because Indic scripts inflect heavily (योजना / योजनाओं / योजनाएं).
# Eligibility is checked first; "पात्र" must not swallow "पात्रता" (a scheme
# search term), hence the negative lookahead.
NATIVE_ELIGIBILITY_PATTERNS = [
    r"पात्र(?!ता)", r"योग्य", r"आवेदन कर सकता", r"मैं पात्र",
    r"தகுதியானவர்",
]

NATIVE_DOCUMENT_PATTERNS = [
    r"दस्तावेज अपलोड", r"प्रमाण पत्र",
]

NATIVE_SCHEME_SEARCH_PATTERNS = [
    # Hindi
    r"योजना", r"स्कीम", r"सब्सिडी", r"लाभ", r"पात्रता", r"आवेदन", r"दस्तावेज",
    r"किसान", r"महिला", r"छात्र", r"शिक्षा", r"आवास", r"स्वास्थ्य", r"रोजगार", r"व्यवसाय",
    # Tamil
    r"திட்ட", r"மானியம்", r"நலன்", r"தகுதி", r"விண்ணப்பம்", r"ஆவணம்",
    r"விவசாயி", r"மகளிர்", r"மாணவர்", r"கல்வி", r"வீட்டுவசதி",
]

# Clearly off-topic messages stay out_of_scope without any model call. Everything else the rules do
# not recognise is "unknown" and goes to the understanding layer / retrieval + citation guard.
OFF_TOPIC_PATTERNS = [
    r"\b(?:weather|wether|forecast)\b", r"\bcricket\b|\bcricekt\b|\bipl\b|\bfootball\b|\bsports?\b",
    r"\b(?:match|live)\s+scores?\b", r"\bwho\s+won\b", r"\bjokes?\b|\bjoek\b", r"\bmovies?\b|\bfilms?\b|\bbollywood\b",
    r"\brecipes?\b|\brecipie\b|\bbiryani\b|\bhow\s+(?:do\s+i|to)\s+cook\b",
    r"\bstock\s+(?:prices?|market)\b|\bshare\s+(?:prices?|market)\b|\bsensex\b|\bnifty\b|\bbitcoin\b",
    r"\bnews\b", r"ignore\s+(?:all\s+|any\s+|the\s+|your\s+)?(?:previous|prior|above)\s+instructions?",
    r"system\s+prompt", r"\bpoems?\b|\bsongs?\b", r"\bpython\b|\bwrite\s+(?:me\s+)?(?:a\s+)?(?:script|code|program)\b",
    r"\bcapital\s+of\b", r"\bgeneral\s+election\b|\bwho\s+will\s+win\b", r"\bresignation\s+letter\b",
    # Hindi / Tamil / Romanized Hindi
    r"मौसम", r"क्रिकेट", r"शेयर\s*बाजार|शेयर\s*बाज़ार", r"फिल्म|फ़िल्म", r"चुटकुला",
    r"வானிலை", r"கிரிக்கெட்", r"பங்குச்?\s*சந்தை", r"திரைப்படம்", r"நகைச்சுவை",
    r"\bmausam\b", r"\bchutkula\b",
]

# Scheme-domain words. A message with one of these is a scheme question even without a trigger phrase
# ("Scholarship for students in Tamil Nadu").
TOPIC_PATTERNS = [
    r"\bscholarships?\b", r"\bstipends?\b", r"\bpensions?\b", r"\bloans?\b", r"\bsubsid(?:y|ies)\b",
    r"\binsurance\b", r"\bhousing\b", r"\beducation\b", r"\bwidows?\b", r"\bdisabled\b|\bdisabilit\w*|\bdivyang\b|\bhandicapped\b",
    r"\bfarm(?:er|ers|ing)\b", r"\bstudents?\b", r"\bwom[ae]n\b", r"\bgirls?\b", r"\bgirl\s+child\b",
    r"\bsc\s*/\s*st\b|\bscheduled\s+(?:caste|tribe)s?\b", r"\bminorit(?:y|ies)\b", r"\bemployment\b|\bunemployed\b",
    r"\bskill\w*\b", r"\btraining\b", r"\bsenior\s+citizens?\b|\belderly\b|\bold\s+age\b", r"\bentrepreneurs?\b",
    r"\bhealth\b", r"\bmaternity\b|\bpregnan\w*\b", r"\bcrops?\b", r"\bartisans?\b|\bweavers?\b|\bfisher\w*\b",
    r"\borphans?\b", r"\bwelfare\b", r"\bfinancial\s+assistance\b", r"\bgrants?\b", r"\bbpl\b",
    # Romanized Hindi
    r"\b(?:chhatravritti|chatravritti|vajifa|vidhwa|vidhva|kisan|mahila|ladki|beti|vikalang|rozgar|rojgar|shiksha|awas|karz|vridha\w*|kaushal)\b",
]

NATIVE_TOPIC_PATTERNS = [
    # Hindi
    r"छात्रवृत्ति", r"पेंशन|पेन्शन", r"ऋण|लोन", r"बीमा", r"विधवा", r"विकलांग|दिव्यांग", r"अल्पसंख्यक", r"बालिका|बेटी|लड़की",
    r"कौशल", r"प्रशिक्षण", r"अनुसूचित", r"वृद्ध|बुजुर्ग", r"भत्ता", r"अनुदान",
    # Tamil
    r"உதவித்தொகை", r"ஓய்வூதியம்", r"கடன்", r"காப்பீடு", r"விதவை", r"மாற்றுத்திறனாளி", r"சிறுபான்மை", r"பெண்",
    r"வேலைவாய்ப்பு", r"திறன்", r"முதியோர்", r"மாணவி",
]

CATEGORY_PATTERNS = {
    "sc": r"\bsc\b|scheduled caste",
    "st": r"\bst\b|scheduled tribe",
    "obc": r"\bobc\b|other backward class",
    "general": r"\bgeneral category\b",
}

GENDER_PATTERNS = {
    "female": r"\bfemale\b|\bwoman\b|\bi\s*am\s*a?\s*girl\b",
    "male": r"\bmale\b|\bman\b|\bi\s*am\s*a?\s*boy\b",
    "other": r"\bnon[- ]binary\b|\bother gender\b|\btransgender\b",
}

AGE_PATTERNS = [
    r"\bi\s*am\s*(\d{1,3})\s*years?\s*old\b",
    r"\bage\s*(?:is|:)?\s*(\d{1,3})\b",
    r"\b(\d{1,3})\s*years?\s*old\b",
]

INCOME_PATTERNS = [
    # Keyword-led: "income of/is/: <amount> [lakh|crore]" or "earn <amount> [...]"
    r"income\s*(?:of|is|:)?\s*(?:rs\.?|₹|rupees)?\s*([\d,]+(?:\.\d+)?)\s*(lakh|lakhs|crore|crores)?",
    r"earn\s*(?:rs\.?|₹|rupees)?\s*([\d,]+(?:\.\d+)?)\s*(lakh|lakhs|crore|crores)?",
    # Bare amount with an explicit unit, e.g. "1.2 lakhs", "2 lakh" — no keyword needed.
    r"(?:rs\.?|₹|rupees)?\s*([\d,]+(?:\.\d+)?)\s*(lakh|lakhs|crore|crores)",
    # A message that is *only* a number (optionally comma-grouped/₹-prefixed), e.g.
    # "1,20,000" or "50000" — the typical reply to a direct income question.
    r"^\s*(?:rs\.?|₹|rupees)?\s*([\d,]{4,}(?:\.\d+)?)\s*()$",
]

MULTIPLIERS = {
    "lakh": 100_000,
    "lakhs": 100_000,
    "crore": 10_000_000,
    "crores": 10_000_000,
}


def _match_any(patterns: list[str], query: str) -> bool:
    return any(re.search(p, query, re.IGNORECASE) for p in patterns)


def extract_entities(query: str) -> dict:
    entities = {}

    for state in STATE_NAMES:
        if state.lower() in query.lower():
            entities["state"] = state
            break

    for category, pattern in CATEGORY_PATTERNS.items():
        if re.search(pattern, query, re.IGNORECASE):
            entities["category"] = category
            break

    for gender, pattern in GENDER_PATTERNS.items():
        if re.search(pattern, query, re.IGNORECASE):
            entities["gender"] = gender
            break

    for pattern in AGE_PATTERNS:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            entities["age"] = int(match.group(1))
            break

    for pattern in INCOME_PATTERNS:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            raw = match.group(1).replace(",", "").strip()
            if not raw:  # bare "," match — skip, try next pattern
                continue
            amount = float(raw)
            unit = (match.group(2) or "").lower()
            multiplier = MULTIPLIERS.get(unit, 1)
            entities["income"] = amount * multiplier
            break

    return entities


def is_detail_request(query: str) -> bool:
    """True for "tell me more about X" / "details of X" style requests (English or native script)."""
    return _match_any(SCHEME_DETAIL_PATTERNS, query) or _match_any(NATIVE_SCHEME_DETAIL_PATTERNS, query)


def classify(query: str) -> dict:
    entities = extract_entities(query)

    if _match_any(OFF_TOPIC_PATTERNS, query):
        return {"intent": "out_of_scope", "confidence": 0.9, "extracted_entities": entities}

    # Native-script pre-check: runs before (and independent of) translation.
    if _match_any(NATIVE_SCHEME_DETAIL_PATTERNS, query):
        return {"intent": "scheme_search", "confidence": 0.85, "extracted_entities": entities}
    if _match_any(NATIVE_ELIGIBILITY_PATTERNS, query):
        return {"intent": "eligibility_check", "confidence": 0.85, "extracted_entities": entities}
    if _match_any(NATIVE_DOCUMENT_PATTERNS, query):
        return {"intent": "document_upload", "confidence": 0.85, "extracted_entities": entities}
    if _match_any(NATIVE_SCHEME_SEARCH_PATTERNS, query):
        return {"intent": "scheme_search", "confidence": 0.85, "extracted_entities": entities}
    if _match_any(NATIVE_TOPIC_PATTERNS, query):
        return {"intent": "scheme_search", "confidence": 0.8, "extracted_entities": entities, "topic_only": True}

    if _match_any(SCHEME_DETAIL_PATTERNS, query):
        return {"intent": "scheme_search", "confidence": 0.9, "extracted_entities": entities}

    if _match_any(ELIGIBILITY_PATTERNS, query):
        return {"intent": "eligibility_check", "confidence": 0.9, "extracted_entities": entities}

    if _match_any(DOCUMENT_PATTERNS, query):
        return {"intent": "document_upload", "confidence": 0.9, "extracted_entities": entities}

    if _match_any(COMPARISON_PATTERNS, query):
        return {"intent": "comparison", "confidence": 0.9, "extracted_entities": entities}

    if _match_any(SCHEME_SEARCH_PATTERNS, query):
        return {"intent": "scheme_search", "confidence": 0.9, "extracted_entities": entities}

    if _match_any(TOPIC_PATTERNS, query):
        return {"intent": "scheme_search", "confidence": 0.8, "extracted_entities": entities, "topic_only": True}

    # No trigger phrase, but the message names a scheme we know: it is a scheme question.
    # "matched_schemes" lets the caller fetch exactly those schemes.
    named = find_schemes_in(query)
    if named:
        return {
            "intent": "scheme_search",
            "confidence": 0.8,
            "extracted_entities": entities,
            "matched_schemes": named,
        }

    # Not recognised and not clearly off-topic: let the understanding layer or retrieval decide.
    return {"intent": "unknown", "confidence": 0.3, "extracted_entities": entities}


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")

    test_queries = [
        "Am I eligible for PM-KISAN?",
        "I want to upload my income certificate",
        "Compare PM-KISAN vs PMAY",
        "What is the Annal Ambedkar Business Champions Scheme?",
        "I am 30 years old, SC category, income of 1.5 lakhs, from Tamil Nadu",
        "asdkjaslkdj random text",
    ]

    for q in test_queries:
        print(f"{q!r} -> {classify(q)}")
