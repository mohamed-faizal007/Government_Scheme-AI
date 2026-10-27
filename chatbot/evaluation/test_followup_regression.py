"""Regression tests for the follow-up / language fixes. Uses the real pipeline (MongoDB, ChromaDB,
Groq, local translation models), so it needs the same environment as eval_rag.

Run: python -m chatbot.evaluation.test_followup_regression  (from repo root)
"""
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from chatbot.backend.api.main import OUT_OF_SCOPE_MESSAGE, _process_message
from chatbot.backend.rag.generator import DECLINE_MESSAGE
from chatbot.backend.router.followup import is_followup, ordinal_index
from chatbot.backend.router.intent_classifier import classify
from chatbot.backend.translation.translator import resolve_language, translate

NAMED_SCHEME = "Farmers Training Institute Scheme"
PAUSE_S = 3.0  # spacing between LLM calls (Groq free tier)


def _has_tamil(text: str) -> bool:
    return any("஀" <= ch <= "௿" for ch in text)


def _is_refusal(result: dict) -> bool:
    return OUT_OF_SCOPE_MESSAGE in result["answer"] or DECLINE_MESSAGE.lower() in result["answer"].lower()


def _chat(message, session_id=None, pill=None, source="typed"):
    time.sleep(PAUSE_S)
    return _process_message(message, session_id, pill, source)


# --- 1. the three transcript messages ---------------------------------------------------------
def test_transcript_router_decisions():
    assert classify("What schemes are available for farmers?")["intent"] == "scheme_search"
    assert classify("who can apply for it?")["intent"] == "scheme_search"
    assert classify(f"Tell me more about {NAMED_SCHEME}")["intent"] == "scheme_search"


def test_transcript_end_to_end():
    first = _chat("What schemes are available for farmers?")
    assert first["intent"] == "scheme_search" and not _is_refusal(first), first["answer"]
    second = _chat("who can apply for it?", first["session_id"])
    assert second["intent"] == "scheme_search" and not _is_refusal(second), second["answer"]
    third = _chat(f"Tell me more about {NAMED_SCHEME}", second["session_id"])
    assert third["language"] == "en" and not _is_refusal(third), third["answer"]
    assert not _has_tamil(third["answer"])
    assert NAMED_SCHEME.lower() in third["answer"].lower()


# --- 2. Tamil pill + typed English -> English ------------------------------------------------
def test_tamil_pill_typed_english_answers_in_english():
    assert resolve_language("What schemes are available for farmers?", "ta", "typed") == "en"
    result = _chat("Can you recommend a good pizza place nearby", pill="ta")  # out of scope: refusal
    assert result["language"] == "en" and not _has_tamil(result["answer"]), result["answer"]
    assert result["answer"] == OUT_OF_SCOPE_MESSAGE


# --- 3. Tamil pill + button click -> Tamil ---------------------------------------------------
def test_tamil_pill_button_click_answers_in_tamil():
    assert resolve_language(f"Tell me more about {NAMED_SCHEME}", "ta", "button") == "ta"
    result = _chat(f"Tell me more about {NAMED_SCHEME}", pill="ta", source="button")
    assert result["language"] == "ta" and _has_tamil(result["answer"]), result["answer"]


def test_short_or_ambiguous_typed_text_uses_pill():
    for text in ("ok", "PM-KISAN", "50000", "thanks"):
        assert resolve_language(text, "ta", "typed") == "ta", text
    assert resolve_language("விவசாயிகளுக்கான திட்டங்கள் என்ன உள்ளன", "en", "typed") == "ta"


# --- 4. follow-up after a farmers search ----------------------------------------------------
def test_followup_is_grounded_in_listed_schemes():
    first = _chat("What schemes are available for farmers?")
    listed = {s["scheme_name"] for s in first["sources"]}
    assert listed, "first answer cited no schemes"
    second = _chat("who can apply for it?", first["session_id"])
    assert not _is_refusal(second), second["answer"]
    cited = {s["scheme_name"] for s in second["sources"]}
    assert cited and cited <= listed, (cited, listed)


def test_followup_detection_rules():
    last = [{"id": "1", "name": "A Scheme"}, {"id": "2", "name": "B Scheme"}]
    assert is_followup("who can apply for it?", last, False)
    assert is_followup("documents needed", last, False)
    assert is_followup("tell me about the second one", last, False)
    assert ordinal_index("tell me about the second one", 2) == 1
    assert ordinal_index("the last one", 2) == 1
    assert not is_followup("who can apply for it?", [], False)  # nothing to refer to
    assert not is_followup("who can apply for it?", last, True)  # names a scheme itself
    assert not is_followup("documents required for farmers", last, False)  # new topic


# --- 5. Tamil refusal keeps both sentences ---------------------------------------------------
def test_tamil_refusal_keeps_both_sentences():
    first = "I can only help with government scheme information, eligibility checks, and document verification."
    second = "For anything else, please check myscheme.gov.in."
    assert OUT_OF_SCOPE_MESSAGE == f"{first} {second}"
    full = translate(OUT_OF_SCOPE_MESSAGE, source_lang="en", target_lang="ta")
    part_one = translate(first, source_lang="en", target_lang="ta")
    assert _has_tamil(part_one) and part_one in full, full  # the first sentence is not dropped
    assert "myscheme.gov.in" in full
    assert full.count("।") + full.count(".") >= 2, full


TESTS = [obj for name, obj in sorted(globals().items()) if name.startswith("test_") and callable(obj)]

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    failed = 0
    for test in TESTS:
        try:
            test()
            print(f"PASS {test.__name__}")
        except Exception:  # noqa: BLE001 - report every failure, keep going
            failed += 1
            print(f"FAIL {test.__name__}")
            traceback.print_exc()
    print(f"\n{len(TESTS) - failed}/{len(TESTS)} passed")
    sys.exit(1 if failed else 0)
