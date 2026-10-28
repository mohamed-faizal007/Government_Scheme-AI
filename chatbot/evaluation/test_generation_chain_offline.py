"""Offline tests for the answer-generation chain (Gemini primary, Groq fallback, Ollama last).

Nothing here calls Groq or Gemini: both SDK clients are replaced by fakes, and Ollama points at a port
nothing listens on. Run with the provider keys unset:

Run: python -m pytest chatbot/evaluation/test_generation_chain_offline.py  (from repo root)
"""
import json
import sys
import time
from pathlib import Path

import httpx
import pytest
from groq import APIStatusError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from chatbot.backend.api import main as api
from chatbot.backend.api.main import _process_message
from chatbot.backend.cache import answer_cache
from chatbot.backend.config import settings
from chatbot.backend.llm import gemini_provider, groq_provider, limits
from chatbot.backend.llm.base import ProviderUnavailable
from chatbot.backend.llm.chain import FallbackChain
from chatbot.backend.llm.factory import get_llm
from chatbot.backend.llm.gemini_provider import GeminiProvider
from chatbot.backend.llm.groq_provider import GroqProvider
from chatbot.backend.llm.ollama_provider import OllamaProvider
from chatbot.backend.nlu import llm_understander as nlu
from chatbot.backend.rag import generator, rag_chain
from chatbot.backend.rag.generator import BUSY_MESSAGES, DECLINE_MESSAGE
from chatbot.backend.router import intent_classifier

FAKE_SCHEME = "Fake Scholarship Scheme"
GOOD = json.dumps({"answer": f"{FAKE_SCHEME} gives a scholarship to students.", "confidence": "high"})
UNGROUNDED = json.dumps({"answer": "Paris is the capital of France.", "confidence": "high"})


class GeminiError(Exception):
    def __init__(self, code, message="boom"):
        super().__init__(message)
        self.code = code


class Script:
    """Records every provider call in order and answers each model from a script of outcomes."""

    def __init__(self):
        self.calls = []  # ("gemini" | "groq", model)
        self.gemini = {}  # model -> outcome, or a list of outcomes used in turn
        self.groq = {}

    @staticmethod
    def _next(table, model):
        outcome = table.get(model, GOOD)
        if isinstance(outcome, list):
            outcome = outcome.pop(0) if len(outcome) > 1 else outcome[0]
        return outcome

    def gemini_calls(self):
        return [m for p, m in self.calls if p == "gemini"]

    def groq_calls(self):
        return [m for p, m in self.calls if p == "groq"]


class _Resp:
    def __init__(self, text):
        self.text = text
        self.usage_metadata = None


class FakeGeminiClient:
    def __init__(self, script):
        self.models = self
        self.script = script

    def generate_content(self, model, contents, config):
        self.script.calls.append(("gemini", model))
        outcome = self.script._next(self.script.gemini, model)
        if outcome == "sleep":
            time.sleep(0.5)
            outcome = GOOD
        if isinstance(outcome, Exception):
            raise outcome
        return _Resp(outcome)


def _groq_error(status, message="rate limit"):
    response = httpx.Response(status, request=httpx.Request("POST", "http://fake"))
    return APIStatusError(message, response=response, body=None)


class FakeGroqClient:
    def __init__(self, script):
        self.script = script
        self.chat = self
        self.completions = self

    def create(self, model, messages):
        self.script.calls.append(("groq", model))
        outcome = self.script._next(self.script.groq, model)
        if isinstance(outcome, Exception):
            raise outcome

        class _Msg:
            content = outcome

        class _Choice:
            message = _Msg()

        class _Completion:
            choices = [_Choice()]
            usage = None

        return _Completion()


@pytest.fixture
def script(monkeypatch):
    s = Script()
    monkeypatch.setattr(settings, "gemini_api_key", "fake-key")
    monkeypatch.setattr(settings, "gemini_model", "g-primary")
    monkeypatch.setattr(settings, "gemini_model_fallback", "g-second")
    monkeypatch.setattr(settings, "gemini_gen_timeout", 6.0)
    monkeypatch.setattr(settings, "gemini_daily_cap", 200)
    monkeypatch.setattr(settings, "generation_primary", "gemini")
    monkeypatch.setattr(settings, "groq_api_key", "fake-key")
    monkeypatch.setattr(settings, "groq_model", "groq-20b")
    monkeypatch.setattr(settings, "groq_fallback_model", "groq-120b")
    monkeypatch.setattr(settings, "ollama_base_url", "http://127.0.0.1:9")  # nothing listens here
    monkeypatch.setattr(nlu, "_get_client", lambda: FakeGeminiClient(s))
    monkeypatch.setattr(groq_provider, "Groq", lambda **kw: FakeGroqClient(s))
    nlu.reset_breaker()
    nlu.reset_daily()
    limits.reset()
    return s


def _hits():
    return [
        {
            "scheme_name": FAKE_SCHEME,
            "section": "overview",
            "source_file": "fake.json",
            "scheme": {"_id": "fake-id-1", "metadata": {"scheme_name": FAKE_SCHEME}, "overview": {"description": "A scholarship."}},
        }
    ]


def _generate(language="en"):
    return generator.generate("scholarship for students", _hits(), language)


# --- chain order ---------------------------------------------------------------------------------
def test_default_order_is_gemini_groq_ollama(script):
    chain = get_llm()
    assert [type(p) for p in chain.providers] == [GeminiProvider, GroqProvider, OllamaProvider]


def test_groq_primary_keeps_the_old_order(script, monkeypatch):
    monkeypatch.setattr(settings, "generation_primary", "groq")
    chain = get_llm()
    assert [type(p) for p in chain.providers] == [GroqProvider, GeminiProvider, OllamaProvider]
    assert chain.generate("p", "s") == GOOD
    assert script.calls == [("groq", "groq-20b")]  # Gemini is never touched when Groq answers


def test_invalid_primary_value_means_gemini():
    assert settings.__class__(GENERATION_PRIMARY="nonsense").generation_primary == "gemini"
    assert settings.__class__(GENERATION_PRIMARY=" Groq ").generation_primary == "groq"


# --- Gemini primary ------------------------------------------------------------------------------
def test_gemini_success_never_calls_groq(script, caplog):
    caplog.set_level("INFO")
    result = _generate()
    assert FAKE_SCHEME in result["answer"] and result["sources"]
    assert script.calls == [("gemini", "g-primary")]
    assert "provider=gemini citation_guard=passed" in caplog.text
    assert "gemini" not in result["answer"].lower()  # the provider is logged, not shown


def test_gemini_timeout_goes_to_groq_at_once(script, monkeypatch):
    monkeypatch.setattr(settings, "gemini_gen_timeout", 0.05)
    script.gemini["g-primary"] = "sleep"
    start = time.monotonic()
    chain = get_llm()
    assert chain.generate("p", "s") == GOOD
    assert time.monotonic() - start < 0.4  # did not wait for the slow call, no retry delay
    assert script.calls == [("gemini", "g-primary"), ("groq", "groq-20b")]
    assert chain.last_provider == "GroqProvider"


@pytest.mark.parametrize("code", [429, 503, 504])
def test_gemini_transient_error_goes_to_groq_without_trying_the_second_gemini_model(script, code):
    script.gemini["g-primary"] = GeminiError(code)
    assert get_llm().generate("p", "s") == GOOD
    assert script.calls == [("gemini", "g-primary"), ("groq", "groq-20b")]


def test_gemini_daily_quota_429_tries_the_other_gemini_model(script):
    script.gemini["g-primary"] = GeminiError(429, "quota exceeded: requests per day")
    assert get_llm().generate("p", "s") == GOOD
    assert script.gemini_calls() == ["g-primary", "g-second"] and script.groq_calls() == []
    get_llm().generate("p", "s")  # g-primary is now skipped until the reset
    assert script.gemini_calls() == ["g-primary", "g-second", "g-second"]


def test_gemini_and_groq_20b_failing_then_groq_120b(script):
    script.gemini["g-primary"] = GeminiError(503)
    script.groq["groq-20b"] = _groq_error(429)
    chain = get_llm()
    assert chain.generate("p", "s") == GOOD
    assert script.calls == [("gemini", "g-primary"), ("groq", "groq-20b"), ("groq", "groq-120b")]


@pytest.mark.parametrize("language", ["en", "hi", "ta"])
def test_everything_failing_shows_the_busy_message(script, language):
    script.gemini["g-primary"] = GeminiError(503)
    script.groq["groq-20b"] = _groq_error(429)
    script.groq["groq-120b"] = _groq_error(429)
    result = _generate(language)
    assert result["busy"] is True and result["answer"] == BUSY_MESSAGES[language]
    assert result["sources"] == [] and result["confidence"] == "low"


# --- breaker and caps (shared with the understanding layer) --------------------------------------
def test_breaker_opens_after_three_failures_then_skips_gemini(script):
    script.gemini["g-primary"] = GeminiError(503)
    for _ in range(3):
        assert get_llm().generate("p", "s") == GOOD
    assert script.gemini_calls() == ["g-primary"] * 3
    assert nlu._breaker_open()
    assert get_llm().generate("p", "s") == GOOD  # served by Groq alone
    assert script.gemini_calls() == ["g-primary"] * 3


def test_understanding_failures_open_the_same_breaker(script):
    for _ in range(3):
        nlu._record(False, True)  # what understand() records on 429/5xx/timeout
    assert get_llm().generate("p", "s") == GOOD
    assert script.gemini_calls() == [] and script.groq_calls() == ["groq-20b"]


def test_success_resets_the_failure_count(script):
    script.gemini["g-primary"] = [GeminiError(503), GeminiError(503), GOOD, GeminiError(503), GeminiError(503)]
    for _ in range(5):
        get_llm().generate("p", "s")
    assert not nlu._breaker_open()  # never 3 in a row


def test_daily_cap_is_shared_with_the_understanding_layer(script, monkeypatch):
    monkeypatch.setattr(settings, "gemini_daily_cap", 2)
    assert nlu._reserve({}) is True  # one understanding request
    assert get_llm().generate("p", "s") == GOOD  # the second (last) request of the day
    assert script.gemini_calls() == ["g-primary"]
    assert get_llm().generate("p", "s") == GOOD  # cap reached: straight to Groq
    assert script.gemini_calls() == ["g-primary"] and script.groq_calls() == ["groq-20b"]
    assert nlu._reserve({}) is False  # and understanding is capped too


def test_generation_requests_count_against_the_daily_counter(script, monkeypatch):
    monkeypatch.setattr(settings, "gemini_daily_cap", 1)
    get_llm().generate("p", "s")
    assert nlu._reserve({}) is False


# --- what is sent --------------------------------------------------------------------------------
def test_id_numbers_in_the_question_are_masked_in_the_prompt():
    prompt = generator._build_prompt("my aadhaar is 1234 5678 9012, which scholarship?", _hits())
    assert "1234 5678 9012" not in prompt and "[number removed]" in prompt
    assert FAKE_SCHEME in prompt


def test_gemini_gets_only_prompt_and_system(script, monkeypatch):
    seen = {}
    client = FakeGeminiClient(script)
    original = client.generate_content

    def spy(model, contents, config):
        seen.update(contents=contents, system=config.system_instruction, thinking=config.thinking_config)
        seen["afc_disabled"] = config.automatic_function_calling.disable
        return original(model, contents, config)

    client.generate_content = spy
    monkeypatch.setattr(nlu, "_get_client", lambda: client)
    GeminiProvider().generate("the prompt", "the system")
    assert seen["contents"] == "the prompt" and seen["system"] == "the system"
    assert seen["afc_disabled"] is True and str(seen["thinking"].thinking_level).endswith("MINIMAL")


# --- citation guard and cache, whichever provider answered ---------------------------------------
@pytest.fixture
def pipeline(script, monkeypatch):
    store = {"puts": []}
    monkeypatch.setattr(rag_chain, "retrieve", lambda query, top_k=4: _hits())
    monkeypatch.setattr(rag_chain, "translate", lambda text, **k: text)
    monkeypatch.setattr(api, "translate", lambda text, **k: text)
    monkeypatch.setattr(api, "find_schemes_in", lambda *a, **k: [])
    monkeypatch.setattr(intent_classifier, "find_schemes_in", lambda *a, **k: [])
    monkeypatch.setattr(answer_cache, "enabled", lambda: True)
    monkeypatch.setattr(answer_cache, "get", lambda key: None)
    monkeypatch.setattr(answer_cache, "put", lambda key, value: store["puts"].append(value))
    return store


def test_guard_approved_gemini_answer_is_cached(script, pipeline):
    result = _process_message("scholarship for students", None, "en")
    assert script.gemini_calls() == ["g-primary"]
    assert FAKE_SCHEME in result["answer"] and len(pipeline["puts"]) == 1
    assert pipeline["puts"][0]["sources"]


def test_guard_approved_groq_answer_is_cached(script, pipeline):
    script.gemini["g-primary"] = GeminiError(503)
    result = _process_message("scholarship for students", None, "en")
    assert script.groq_calls() == ["groq-20b"]
    assert FAKE_SCHEME in result["answer"] and len(pipeline["puts"]) == 1


@pytest.mark.parametrize("who", ["gemini", "groq"])
def test_ungrounded_answer_is_replaced_and_not_cached(script, pipeline, who):
    if who == "gemini":
        script.gemini["g-primary"] = UNGROUNDED
    else:
        script.gemini["g-primary"] = GeminiError(503)
        script.groq["groq-20b"] = UNGROUNDED
    result = _process_message("scholarship for students", None, "en")
    assert DECLINE_MESSAGE in result["answer"] and result["sources"] == []
    assert pipeline["puts"] == []


def test_busy_message_is_not_cached(script, pipeline):
    script.gemini["g-primary"] = GeminiError(503)
    script.groq["groq-20b"] = _groq_error(429)
    script.groq["groq-120b"] = _groq_error(429)
    result = _process_message("scholarship for students", None, "en")
    assert result["answer"] == BUSY_MESSAGES["en"] and pipeline["puts"] == []
