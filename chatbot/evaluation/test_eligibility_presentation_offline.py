"""Offline tests for the eligibility answer after a document upload: extraction, carry-over, topic handling,
presentation and wording.

Nothing here calls Groq, Gemini or Ollama: the extraction client, retrieval and translation are fakes, and the
engine under test is the deterministic rules engine.

Run: python -m pytest chatbot/evaluation/test_eligibility_presentation_offline.py  (from repo root)
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from chatbot.backend.api import main as api
from chatbot.backend.api.main import _get_session, _process_message
from chatbot.backend.cache import answer_cache
from chatbot.backend.config import settings
from chatbot.backend.documents import extractor
from chatbot.backend.eligibility import presentation as pres
from chatbot.backend.eligibility.rules_engine import check_eligibility
from chatbot.backend.eligibility.user_profile import UserProfile
from chatbot.backend.nlu import llm_understander as nlu
from chatbot.backend.retrieval import scheme_states

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
INCOME_DOC = """INCOME CERTIFICATE
Name: Ravi Kumar S/O Murugan
Sex: M
Age: 34 years
Occupation: Farmer
Community: OBC
Annual Income: Rs. 1,80,000
State: Tamil Nadu"""

STUDENT_DOC_NO_CATEGORY = """STUDENT DETAILS
Name: Priya D/O Selvam
Gender: Female
Age: 19
Occupation: Student
State: Tamil Nadu
Family income: Rs. 2,00,000"""


class FakeClient:
    """Stands in for the Instructor/Groq client; returns the canned extraction and records calls."""

    def __init__(self, result):
        self.result = result
        self.calls = 0
        self.chat = self
        self.completions = self

    def create(self, **kwargs):
        self.calls += 1
        return self.result


def _extraction(**kw):
    base = dict(
        age=None, income_annual=None, category=None, state=None, gender=None, occupation=None,
        age_confidence=0.0, income_annual_confidence=0.0, category_confidence=0.0, state_confidence=0.0,
        gender_confidence=0.0, occupation_confidence=0.0,
    )
    base.update(kw)
    return extractor._ExtractionResult(**base)


def _upload(monkeypatch, text, result, profile=None):
    client = FakeClient(result)
    monkeypatch.setattr(extractor, "_get_client", lambda: client)
    extracted = extractor.extract_fields(text)
    return extracted, extractor.autofill_profile(extracted, profile or UserProfile())


def scheme(name, conditions=None, exclusions=None, tags=None, category="", benefit=""):
    return {
        "_id": name,
        "metadata": {"scheme_name": name, "scheme_type": "", "state": "", "implementing_department": "", "category": category},
        "benefits": {"financial_assistance": benefit, "other_benefits": []},
        "eligibility": {"conditions": conditions or [], "exclusions": exclusions or []},
        "search_metadata": {"tags": tags or [], "keywords": []},
    }


def hit(sch):
    return {"scheme": sch, "scheme_name": sch["metadata"]["scheme_name"], "section": "eligibility", "source_file": "x.json", "score": 1.0}


FARM = scheme(
    "Kisan Support Scheme",
    conditions=["Applicant must be a farmer", "Annual income not exceeding Rs. 3 lakh"],
    tags=["Agriculture", "Farmer"],
    category="Agriculture",
    benefit="Rs. 6,000 per year in three instalments. Paid directly to the bank account.",
)
BUSINESS = scheme("Unemployed Youth Business Loan", conditions=["Age between 18 and 35 years"], tags=["Business", "Loan"], category="Loan")
STUDENT = scheme("Merit Scholarship", conditions=["Annual income not exceeding Rs. 5 lakh"], tags=["Education", "Scholarship"], category="Scholarship")


@pytest.fixture
def chat(monkeypatch):
    """Fake retrieval (records queries) and translation; no LLM anywhere."""
    state = {"queries": [], "calls": [], "hits": [hit(BUSINESS), hit(FARM), hit(STUDENT)]}

    def fake_retrieve(query, top_k=4, filters=None, scheme_ids=None):
        state["queries"].append(query)
        state["calls"].append({"top_k": top_k, "scheme_ids": scheme_ids})
        hits = [h for h in state["hits"] if scheme_ids is None or h["scheme"]["_id"] in scheme_ids]
        return hits[:top_k]

    monkeypatch.setattr(api, "retrieve", fake_retrieve)
    # the state index is built from whatever hits the test installs, with the real classifier
    monkeypatch.setattr(api, "_state_index", lambda: scheme_states.build_index(h["scheme"] for h in state["hits"]))
    monkeypatch.setattr(api, "translate", lambda text, **k: text)
    monkeypatch.setattr(api, "find_schemes_in", lambda *a, **k: [])
    monkeypatch.setattr(answer_cache, "enabled", lambda: False)
    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.setattr(settings, "groq_api_key", "")
    monkeypatch.setattr(nlu, "understand", lambda *a, **k: None)
    return state


def full_profile(**kw):
    base = dict(age=34, gender="male", state="Tamil Nadu", income_annual=180_000, category="obc")
    base.update(kw)
    return UserProfile(**base)


def seed_session(profile):
    sid, session = _get_session(None)
    session["profile"] = profile
    return sid, session


# ---------------------------------------------------------------------------
# 1. extraction: gender / occupation / category are read and reported
# ---------------------------------------------------------------------------
def test_gender_occupation_category_are_extracted_and_reported(monkeypatch):
    result = _extraction(
        age=34, age_confidence=0.95, income_annual=180000, income_annual_confidence=0.95, state="Tamil Nadu",
        state_confidence=0.95, gender="male", gender_confidence=0.9, occupation="Farmer", occupation_confidence=0.9,
        category="OBC", category_confidence=0.9,
    )
    extracted, fill = _upload(monkeypatch, INCOME_DOC, result)
    profile = fill["updated_profile"]
    assert (profile.gender, profile.occupation, profile.category) == ("male", "farmer", "obc")
    assert set(fill["high_confidence_fills"]) == {"age", "income_annual", "category", "state", "gender", "occupation"}
    message = pres.upload_message(fill)
    for expected in ("gender: Male", "occupation: farmer", "category: OBC", "age: 34"):
        assert expected in message


def test_bc_is_normalised_to_obc_only_when_the_document_says_bc(monkeypatch):
    result = _extraction(category="BC", category_confidence=0.9)
    _, fill = _upload(monkeypatch, "Community: BC\nName: A", result)
    assert fill["updated_profile"].category == "obc"
    # ...and the value must be one the scheme data / engine uses
    assert fill["updated_profile"].category in {"general", "obc", "sc", "st"}


def test_unknown_category_value_is_dropped(monkeypatch):
    _, fill = _upload(monkeypatch, "Community: Brahmin", _extraction(category="Brahmin", category_confidence=0.9))
    assert fill["updated_profile"].category is None


# ---------------------------------------------------------------------------
# 2. carry-over: overwrite what the file has, never invent what it lacks
# ---------------------------------------------------------------------------
def test_upload_without_category_does_not_invent_one_even_if_model_guesses(monkeypatch):
    guessed = _extraction(age=19, age_confidence=0.9, category="obc", category_confidence=0.9,
                          gender="female", gender_confidence=0.9, occupation="student", occupation_confidence=0.9)
    extracted, fill = _upload(monkeypatch, STUDENT_DOC_NO_CATEGORY, guessed)
    assert extracted["fields"].category is None  # no evidence in the text -> dropped
    assert fill["updated_profile"].category is None
    assert "category" in fill["failed_fields"]
    assert fill["updated_profile"].gender == "female" and fill["updated_profile"].occupation == "student"


def test_earlier_values_survive_and_are_visible_in_the_confirmation(monkeypatch):
    earlier = UserProfile(category="obc", age=40)
    result = _extraction(age=19, age_confidence=0.9, occupation="student", occupation_confidence=0.9)
    _, fill = _upload(monkeypatch, STUDENT_DOC_NO_CATEGORY, result, profile=earlier)
    profile = fill["updated_profile"]
    assert profile.category == "obc"  # carried over, not invented
    assert profile.age == 19  # overwritten by the new document
    message = pres.upload_message(fill)
    assert "category: OBC" in message and "age: 19" in message and "occupation: student" in message
    assert "Not found in the document: " in message and "category" in message.split("Not found in the document: ")[1]


def test_new_conversation_gets_an_empty_profile():
    old_id, old = _get_session(None)
    old["profile"] = full_profile()
    new_id, new = _get_session(None)  # the frontend asks for a fresh session id on "New conversation"
    assert new_id != old_id
    assert all(v is None for v in new["profile"].model_dump().values())


# ---------------------------------------------------------------------------
# 3. no-topic eligibility
# ---------------------------------------------------------------------------
def test_farmer_profile_uses_agriculture_as_topic_and_filter(chat):
    sid, _ = seed_session(full_profile(occupation="farmer"))
    result = _process_message("Which schemes am I eligible for?", sid, "en")
    assert result["intent"] == "eligibility_check"
    assert chat["queries"][0] == "agriculture schemes"
    names = [r["scheme_name"] for r in result["eligibility_results"]]
    assert names == ["Kisan Support Scheme"]  # business loan and scholarship are filtered out
    assert "Unemployed Youth Business Loan" not in result["answer"]
    assert "occupation (farmer)" in result["answer"]


def test_student_hint_maps_to_education():
    assert pres.topic_hint(UserProfile(occupation="Student")) == "education"
    assert pres.topic_hint(UserProfile(is_student=True)) == "education"
    assert pres.topic_hint(UserProfile(occupation="farmer")) == "agriculture"
    assert pres.topic_hint(UserProfile()) is None


def test_no_hint_asks_for_the_area_with_chips_then_continues(chat):
    sid, session = seed_session(full_profile())
    first = _process_message("Which schemes am I eligible for?", sid, "en")
    assert first["answer"] == "Which area are you interested in? (farming, education, housing, business, health, pension...)"
    assert [c["value"] for c in first["quick_replies"]] == ["farming", "education", "housing", "business", "health", "pension"]
    assert first["eligibility_results"] == [] and chat["queries"] == []  # nothing unrelated was retrieved

    second = _process_message("farming", sid, "en")
    assert chat["queries"][0] == "agriculture schemes"
    assert [r["scheme_name"] for r in second["eligibility_results"]] == ["Kisan Support Scheme"]
    assert not session.get("awaiting_topic")


def test_named_topic_is_left_alone(chat):
    sid, _ = seed_session(full_profile(occupation="farmer"))
    _process_message("Am I eligible for a scholarship?", sid, "en")
    assert chat["queries"][0] == "Am I eligible for a scholarship?"


# ---------------------------------------------------------------------------
# 5. fragment filter (presentation layer only)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("fragment", [
    "What is the purpose of this scheme?",
    "Note 01: documents must be original",
    "Step-1: register on the portal",
    "Obligation of an applicant under the scheme",
    "How can I apply for this scheme online",
    "Whether the applicant has land in own name",
    "Can the applicant apply for more than one scheme",
    "The applicant must hold a valid certificate issued by the...",
    "Applicant should have a bank account linked with Aadhaar and must submit all the supporting documents "
    "within thirty days of the date of application failing which the application will be rejected outright and "
    "the applicant will have to reapply in the following financial year",
])
def test_boilerplate_fragments_are_dropped_or_shortened(fragment):
    cleaned = pres.clean_condition(fragment)
    if cleaned is not None:  # only an over-long but otherwise real condition survives, shortened
        assert len(fragment) > 160 and len(cleaned) <= 123 and cleaned.endswith("...")
    else:
        assert fragment != "Applicant should have a bank account"


def test_real_conditions_are_kept_and_long_real_ones_shortened():
    assert pres.clean_condition("Applicant should be a resident of Tamil Nadu") == "Applicant should be a resident of Tamil Nadu"
    long_real = "Applicant must be a small or marginal farmer owning cultivable land " + "in the notified districts " * 8
    shortened = pres.clean_condition(long_real)
    assert shortened.endswith("...") and len(shortened) <= 123
    assert pres.clean_condition("Is this open to all?") is None


def test_engine_tail_ellipsis_is_not_mistaken_for_source_truncation():
    engine_cut = ("Applicant must belong to a family whose annual income from all sources is verified by the "
                  "revenue authority every year and is certified")[:120] + "..."
    assert len(engine_cut) == 123
    assert pres.clean_condition(engine_cut) == engine_cut
    assert pres.clean_condition("The applicant shall submit the form to the... office") is None


def test_filter_conditions_dedupes_and_cap_message(chat):
    conditions = [f"Applicant must satisfy criterion number {n} of the notified list" for n in range(1, 8)] + [
        "What is the last date?", "Note 02", "Step-3: upload documents"]
    sch = scheme("Many Conditions Scheme", conditions=conditions, tags=["Agriculture"])
    chat["hits"] = [hit(sch)]
    sid, _ = seed_session(full_profile(occupation="farmer"))
    answer = _process_message("Which schemes am I eligible for?", sid, "en")["answer"]
    assert answer.count("\n- ") == 3
    assert "4 more conditions could not be checked automatically; see the scheme page." in answer
    assert "Step-3" not in answer and "last date" not in answer


# ---------------------------------------------------------------------------
# 4 + 6. presentation and wording
# ---------------------------------------------------------------------------
def make_entries(statuses):
    entries = []
    for i, status in enumerate(statuses):
        entries.append({
            "scheme_name": f"Scheme {i}", "hit": {}, "benefit": None, "status": status, "conditions": [],
            "missing": [], "failed": ["Age between 18 and 35 years"], "eligible": status != "not",
        })
    return entries


def test_at_most_five_eligible_and_may_first_and_not_eligible_hidden():
    entries = make_entries(["not", "may", "eligible", "not", "may", "eligible", "may", "eligible"])
    text, shown = pres.render_answer(entries, "en")
    assert len(shown) == 5
    assert [e["status"] for e in shown] == ["eligible"] * 3 + ["may"] * 2
    assert "do not appear to be eligible." not in text
    assert "I left out 2 scheme(s)" in text


def test_not_eligible_listed_only_on_request_or_when_nothing_else():
    entries = make_entries(["not", "may"])
    text, shown = pres.render_answer(entries, "en", show_not=True)
    assert [e["status"] for e in shown] == ["may", "not"] and "You do not appear to be eligible." in text
    only_bad = make_entries(["not", "not"])
    text, shown = pres.render_answer(only_bad, "en")
    assert len(shown) == 2 and text.split("\n\n")[0].startswith("I could not find a scheme you are eligible for")
    assert pres.wants_not_eligible("show schemes I'm not eligible for")
    assert not pres.wants_not_eligible("which schemes am I eligible for")


def test_show_not_eligible_request_goes_through_the_chat(chat):
    sid, _ = seed_session(full_profile(age=60, occupation="farmer"))
    chat["hits"] = [hit(FARM), hit(scheme("Youth Farm Grant", conditions=["Age between 18 and 35 years"], tags=["Agriculture"]))]
    default = _process_message("Which schemes am I eligible for?", sid, "en")["answer"]
    assert "Youth Farm Grant" not in default and "I left out 1 scheme(s)" in default
    asked = _process_message("show schemes I'm not eligible for", sid, "en")["answer"]
    assert "Youth Farm Grant" in asked and "You do not appear to be eligible." in asked


def test_wording_may_vs_appear_and_missing_fields():
    unknown_age = scheme("Age Rule Scheme", conditions=["Age between 18 and 35 years", "Must belong to SC category"], tags=["Agriculture"])
    profile = UserProfile(state="Tamil Nadu", income_annual=100000)
    entry = pres.make_entry(hit(unknown_age), check_eligibility(profile, unknown_age), profile)
    assert entry["status"] == "may" and set(entry["missing"]) == {"age", "category"}
    text, _ = pres.render_answer([entry], "en")
    assert "You may be eligible." in text and "appear to be ELIGIBLE" not in text
    assert "Missing details: age, category." in text and "Tell me these" in text

    clean = scheme("Clean Scheme", conditions=["Age between 18 and 60 years"])
    profile = UserProfile(age=30)
    entry = pres.make_entry(hit(clean), check_eligibility(profile, clean), profile)
    assert entry["status"] == "eligible"
    assert "You appear to be eligible." in pres.render_answer([entry], "en")[0]

    failing = scheme("Failing Scheme", conditions=["Age between 18 and 25 years"])
    entry = pres.make_entry(hit(failing), check_eligibility(profile, failing), profile)
    assert entry["status"] == "not"
    assert "You do not appear to be eligible." in pres.render_answer([entry], "en", show_not=True)[0]


def test_a_scheme_with_nothing_checked_is_never_plain_eligible():
    empty = scheme("Empty Scheme", conditions=[])
    entry = pres.make_entry(hit(empty), check_eligibility(UserProfile(age=30), empty), UserProfile(age=30))
    assert entry["status"] == "may"


@pytest.mark.parametrize("language", ["hi", "ta"])
def test_hi_ta_templates_keep_scheme_names_verbatim(language):
    entry = make_entries(["may"])[0]
    entry.update(scheme_name="PM-KISAN Samman Nidhi", missing=["age", "category"], conditions=["Cond A is real", "Cond B is real"])
    text, _ = pres.render_answer([entry], language)
    assert "**PM-KISAN Samman Nidhi**" in text
    assert pres.T[language]["may"] in text
    assert pres.FIELD_LABELS[language]["age"] in text and "age," not in text
    question, chips = pres.topic_question(language)
    assert question == pres.T[language]["ask_topic"] and len(chips) == 6
    assert all(c["value"].isascii() for c in chips)  # English values are what get sent back
    assert pres.T[language]["not"] != pres.T["en"]["not"] and pres.T[language]["eligible"] != pres.T["en"]["eligible"]


def test_unverified_conditions_capped_at_three():
    entry = make_entries(["may"])[0]
    entry["conditions"] = [f"Real condition number {n} about the applicant" for n in range(5)]
    text, _ = pres.render_answer([entry], "en")
    assert text.count("\n- ") == 3 and "2 more conditions could not be checked automatically; see the scheme page." in text


def test_one_line_benefit_is_shown():
    assert pres.benefit_line(FARM) == "Rs. 6,000 per year in three instalments."
    assert pres.benefit_line(scheme("No Benefit")) is None


# ---------------------------------------------------------------------------
# state scope: the user's state plus central schemes, many candidates, best five shown
# ---------------------------------------------------------------------------
def farm_scheme(name, conditions, benefit=""):
    return scheme(name, conditions=conditions, tags=["Agriculture", "Farmer"], category="Agriculture", benefit=benefit)


MEGHALAYA = [farm_scheme(f"Meghalaya Farm Scheme {n}", ["Applicant must be a resident of Meghalaya"]) for n in range(1, 4)]
TN_ELIGIBLE = farm_scheme("Tamil Nadu Farmer Grant", ["Applicant must be a resident of Tamil Nadu", "Age between 18 and 60 years"])
TN_MAY = farm_scheme("Tamil Nadu Land Support", ["Applicant must be a resident of Tamil Nadu", "Must own at least two acres of land"])
CENTRAL_ELIGIBLE = farm_scheme("Central Farmer Income Support", ["Annual income not exceeding Rs. 3 lakh"])
CENTRAL_MAY = farm_scheme("Central Crop Insurance", ["Must have a valid crop sowing certificate"])


def test_tamil_nadu_farmer_sees_only_tn_and_central_schemes_best_first(chat):
    # Meghalaya schemes rank first in retrieval, as in the reported bug; the scope must drop them
    chat["hits"] = [hit(s) for s in MEGHALAYA + [CENTRAL_MAY, TN_MAY, CENTRAL_ELIGIBLE, TN_ELIGIBLE]]
    sid, _ = seed_session(full_profile(age=30, income_annual=150000, occupation="farmer"))
    result = _process_message("Which schemes am I eligible for?", sid, "en")
    names = [r["scheme_name"] for r in result["eligibility_results"]]
    assert not any("Meghalaya" in n for n in names) and "Meghalaya" not in result["answer"]
    assert set(names) == {"Tamil Nadu Farmer Grant", "Central Farmer Income Support", "Tamil Nadu Land Support", "Central Crop Insurance"}
    statuses = [r["status"] for r in result["eligibility_results"]]
    assert statuses == ["eligible", "eligible", "may", "may"]  # eligible above may-be-eligible
    assert names[:2] == ["Central Farmer Income Support", "Tamil Nadu Farmer Grant"] or names[:2] == ["Tamil Nadu Farmer Grant", "Central Farmer Income Support"]
    assert "no schemes specific to" not in result["answer"]
    call = chat["calls"][0]
    assert call["top_k"] == settings.eligibility_candidates == 30 and call["scheme_ids"] is not None


def test_state_with_no_schemes_says_so_and_shows_central_only(chat):
    chat["hits"] = [hit(s) for s in MEGHALAYA + [CENTRAL_MAY, TN_ELIGIBLE, CENTRAL_ELIGIBLE]]
    sid, _ = seed_session(full_profile(state="Kerala", age=30, income_annual=150000, occupation="farmer"))
    result = _process_message("Which schemes am I eligible for?", sid, "en")
    names = [r["scheme_name"] for r in result["eligibility_results"]]
    assert set(names) == {"Central Farmer Income Support", "Central Crop Insurance"}
    assert "I found no schemes specific to Kerala in my data" in result["answer"]


def test_all_candidates_are_evaluated_and_best_five_shown_by_fewest_unverified(chat):
    # 12 candidates; the only fully eligible one is last in retrieval order and must still come first
    maybe = [farm_scheme(f"Farm Scheme {n}", [f"Must hold land record number {n}-{k} issued locally" for k in range(1 + (n * 7) % 4)])
             for n in range(11)]
    best = farm_scheme("Eligible Farm Scheme", ["Age between 18 and 60 years"])
    chat["hits"] = [hit(s) for s in maybe + [best]]
    sid, _ = seed_session(full_profile(age=30, occupation="farmer"))
    result = _process_message("Which schemes am I eligible for?", sid, "en")
    results = result["eligibility_results"]
    assert len(results) == 5 and results[0]["scheme_name"] == "Eligible Farm Scheme" and results[0]["status"] == "eligible"
    counts = [len(r["reasons"]) for r in results[1:]]
    assert counts == sorted(counts)  # fewest unverified conditions first


def test_not_eligible_entries_show_only_failed_conditions():
    sch = scheme("Mixed Scheme", conditions=["Age between 18 and 25 years", "Must own at least two acres of land"], tags=["Agriculture"])
    profile = UserProfile(age=40)
    engine = check_eligibility(profile, sch)
    assert engine["failed_conditions"] == ["Age between 18 and 25 years"] and engine["unverifiable_conditions"]
    entry = pres.make_entry(hit(sch), engine, profile)
    text, _ = pres.render_answer([entry], "en", show_not=True)
    assert "Age between 18 and 25 years" in text and "two acres" not in text


def test_scheme_states_use_whole_words_and_central_means_no_state():
    assert scheme_states.scheme_states(farm_scheme("Goal Oriented Scheme", ["Meet the goals of the programme"])) == frozenset()
    assert scheme_states.scheme_states(farm_scheme("X - Tamil Nadu", ["Resident of Kerala"])) == {"Tamil Nadu", "Kerala"}
    index = scheme_states.build_index(MEGHALAYA + [TN_ELIGIBLE, CENTRAL_MAY])
    scope = scheme_states.scope_for_state(index, "tamil nadu")
    assert (scope["state_count"], scope["central_count"]) == (1, 1) and "Meghalaya Farm Scheme 1" not in scope["ids"]


def test_pattern_of_assistance_label_is_dropped_and_truncation_kept():
    labelled = scheme("L", benefit="")
    labelled["benefits"]["other_benefits"] = ["Pattern of Assistance:Free short-term training to educated unemployed rural youth."]
    assert pres.benefit_line(labelled) == "Free short-term training to educated unemployed rural youth."
    long = scheme("Long")
    long["benefits"]["other_benefits"] = ["Pattern of Assistance:" + "Subsidy on farm machinery purchase " * 6]
    line = pres.benefit_line(long)
    assert not line.startswith("Pattern") and len(line) <= 123 and line.endswith("...")


# ---------------------------------------------------------------------------
# 7. the eligibility engine itself is unchanged: the 20 labelled cases (no model involved)
# ---------------------------------------------------------------------------
def test_engine_accuracy_still_19_of_20():
    from chatbot.evaluation.eval_eligibility import TEST_CASES, _load

    correct = sum(
        check_eligibility(profile, _load(scheme_file))["eligible"] == expected
        for _, scheme_file, profile, expected in TEST_CASES
    )
    assert len(TEST_CASES) == 20 and correct == 19
