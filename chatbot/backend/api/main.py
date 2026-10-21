"""FastAPI backend — chat, profile, health, and WebSocket endpoints.
Run: uvicorn chatbot.backend.api.main:app --reload --port 8000  (from repo root)
"""
import asyncio
import hmac
import logging
import re
import tempfile
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.websockets import WebSocketState

from ..config import settings
from ..database.load_chroma import COLLECTION_NAME as CHROMA_COLLECTION_NAME
from ..database.mongo_client import get_db, get_schemes_collection
from ..documents.extractor import autofill_profile, extract_fields
from ..documents.ocr import extract_text
from ..eligibility.rules_engine import _is_junk, check_eligibility
from ..eligibility.slot_filler import QUESTIONS, get_next_slot
from ..eligibility.slot_parser import EXAMPLES, is_skip, parse_slot_reply
from ..eligibility.user_profile import UserProfile
from ..rag.rag_chain import answer as rag_answer
from ..retrieval.retriever import retrieve
from ..router.intent_classifier import classify
from ..sync import scheduler as sync_scheduler
from ..sync import sync_status
from ..translation.translator import detect_language, translate

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # The scheduler runs on its own daemon thread; failing to start it must not stop the API.
    if settings.sync_scheduler_enabled:
        sync_scheduler.start_scheduler()
    yield
    sync_scheduler.stop_scheduler()


app = FastAPI(title="Government Scheme AI Chatbot", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Session management — in-memory only, no conversation persistence.
# ---------------------------------------------------------------------------
SESSION_TIMEOUT = timedelta(minutes=30)
MAX_MESSAGE_LENGTH = 1000

PROMPT_INJECTION_PATTERNS = [
    "ignore previous instructions",
    "you are now",
    "pretend you are",
    "disregard your",
]

INJECTION_DECLINE_MESSAGE = (
    "I can't process that message. Please ask a question about government "
    "schemes, eligibility, or document verification."
)

OUT_OF_SCOPE_MESSAGE = (
    "I can only help with government scheme information, eligibility checks, "
    "and document verification. For anything else, please check "
    "myscheme.gov.in."
)

COMPARISON_PROMPT_ADDITION = (
    "The user wants to compare multiple schemes. List each scheme separately "
    "with its key benefits and eligibility, then summarize the key differences."
)

DOCUMENT_UPLOAD_PROMPT = (
    "Please upload your document (PDF) using the file upload option so I can "
    "verify it and help fill in your profile."
)

_sessions: dict[str, dict] = {}
# Serialises WebSocket processing per session_id now that _process_message runs in a worker thread.
_ws_session_locks: dict[str, asyncio.Lock] = {}


def _new_session() -> dict:
    return {
        "profile": UserProfile(),
        "history": [],
        "last_active": datetime.now(timezone.utc),
        "last_intent": None,
        "last_bot_message_was_question": False,
        "last_slot_asked": None,
        "eligibility_query": None,
        "slot_failures": {},
        "skipped_slots": set(),
    }


def _purge_expired_sessions() -> None:
    now = datetime.now(timezone.utc)
    expired = [
        sid
        for sid, s in _sessions.items()
        if now - s["last_active"] > SESSION_TIMEOUT
    ]
    for sid in expired:
        del _sessions[sid]


def _get_session(session_id: Optional[str]) -> tuple[str, dict]:
    _purge_expired_sessions()
    if session_id and session_id in _sessions:
        session = _sessions[session_id]
        session["last_active"] = datetime.now(timezone.utc)
        return session_id, session

    new_id = session_id or str(uuid.uuid4())
    session = _new_session()
    _sessions[new_id] = session
    return new_id, session


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    language: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    sources: list = Field(default_factory=list)
    confidence: str
    intent: str
    language: str
    session_id: str
    profile: dict = Field(default_factory=dict)
    eligibility_results: list = Field(default_factory=list)


class FeedbackRequest(BaseModel):
    session_id: str
    message_index: int = Field(ge=0)
    rating: Literal["positive", "negative"]
    query: str = ""
    intent: str = ""


class ProfileRequest(BaseModel):
    session_id: Optional[str] = None
    profile: UserProfile


class ProfileResponse(BaseModel):
    session_id: str
    profile: UserProfile
    message: str = "Profile updated."


# ---------------------------------------------------------------------------
# Core message handling — shared by POST /chat and WS /ws/chat
# ---------------------------------------------------------------------------
def _contains_injection(message: str) -> bool:
    lowered = message.lower()
    return any(pattern in lowered for pattern in PROMPT_INJECTION_PATTERNS)


ENTITY_TO_PROFILE_FIELD = {
    "age": "age",
    "state": "state",
    "income": "income_annual",
    "category": "category",
    "gender": "gender",
}


def _is_non_latin_script(text: str) -> bool:
    return any(ord(ch) > 0x2FF for ch in text)


def _is_translation_failed(original: str, translated: str, language: str) -> bool:
    """True when inward translation produced nothing usable for the English classifier."""
    if language == "en" or not _is_non_latin_script(original):
        return False
    if translated.strip() == original.strip():
        return True  # translate() silently returned the input
    return len(translated.split()) < 3  # too short to carry intent

def _strip_stray_asterisks(text: str) -> str:
    """Remove markdown '*' left unmatched by translation; balanced '**bold**' pairs are kept."""
    out = []
    for line in text.split("\n"):
        bullet = re.match(r"^(\s*)[*]\s+(?=\S)", line)
        prefix = f"{bullet.group(1)}- " if bullet else ""
        body = line[bullet.end():] if bullet else line
        pairs = re.findall(r"[*]{2}(?=[^*\s])[^*]+?(?<=[^*\s])[*]{2}", body)
        parts = re.split(r"([*]{2}(?=[^*\s])[^*]+?(?<=[^*\s])[*]{2})", body)
        body = "".join(p if p in pairs else p.replace("*", "") for p in parts)
        out.append(prefix + body)
    return "\n".join(out)


def _apply_entities(profile: UserProfile, entities: dict) -> None:
    for entity_key, profile_field in ENTITY_TO_PROFILE_FIELD.items():
        if entity_key in entities:
            setattr(profile, profile_field, entities[entity_key])


MAX_SLOT_FAILURES = 3

# "actually, for education" / "instead for health schemes": swaps the topic mid-flow.
TOPIC_CHANGE_RE = re.compile(
    r"^\s*(?:(?:actually|instead|rather)\b[\s,.:-]*for\s+\S|change(?: it)? to\s+\S)", re.IGNORECASE
)
_LEADING_FILLER_RE = re.compile(r"^\s*(?:actually|instead|rather|change(?: it)? to)\b[\s,.:-]*", re.IGNORECASE)
# Words left after removing these mean the question names no topic ("Am I eligible for any scheme?").
_TOPICLESS_RE = re.compile(
    r"am i eligible|do i qualify|can i apply|check eligibility|eligible|for|any|a|an|the|my|me|i|am|to|"
    r"government|govt|central|state|scheme|schemes|yojana|yojna|benefit|benefits|which|what|is|are|there|"
    r"available|can|apply|qualify|get|anything|something|some|please|schemes?",
    re.IGNORECASE,
)
NO_TOPIC_NOTE = (
    "You didn't name a topic, so I searched for schemes matching your profile ({profile}) "
    "instead of a specific area like housing or education."
)


def _topic_change_query(text: str) -> str:
    stripped = _LEADING_FILLER_RE.sub("", text).strip(" ?.!")
    return f"schemes {stripped}" if stripped.lower().startswith("for ") else stripped


def _has_topic(question: str) -> bool:
    if _is_non_latin_script(question):
        return True  # cannot judge native-script wording; assume a topic
    words = re.findall(r"[a-z]+", question.lower())
    return any(not _TOPICLESS_RE.fullmatch(w) for w in words)


def _profile_search_query(profile: UserProfile) -> tuple[str, str]:
    """A generic query built from the profile, plus a readable description of what it used."""
    category = {"sc": "SC", "st": "ST", "obc": "OBC", "general": "general category"}.get(
        (profile.category or "").lower(), profile.category
    )
    query = "schemes" + (f" for {category}" if category else "") + (f" in {profile.state}" if profile.state else "")
    used = ", ".join(x for x in (category, profile.state) if x) or "no details given"
    return query, used


def _slot_prompt(session: dict, slot: str) -> str:
    """The question for `slot`, escalating: plain -> with an example -> with a skip offer."""
    failures = session["slot_failures"].get(slot, 0)
    question = QUESTIONS[slot]
    if failures == 1:
        return f"Sorry, I couldn't understand that. {question} ({EXAMPLES[slot]})"
    if failures >= 2:
        return (
            f"I still couldn't read that. {question} ({EXAMPLES[slot]}). "
            "Or reply \"skip\" and I'll continue without it."
        )
    return question


def _fill_asked_slot(session: dict, profile: UserProfile, text: str) -> None:
    """Interpret `text` as the reply to the slot the bot just asked; track failures and skips."""
    slot = session.get("last_slot_asked")
    if slot is None:
        return
    if is_skip(text):
        session["skipped_slots"].add(slot)
        return
    value = parse_slot_reply(slot, text)
    if value is not None:
        setattr(profile, slot, value)
    elif getattr(profile, slot) is None:  # entities from the full message may have filled it already
        failures = session["slot_failures"].get(slot, 0) + 1
        session["slot_failures"][slot] = failures
        if failures >= MAX_SLOT_FAILURES:
            session["skipped_slots"].add(slot)  # never loop forever


def _handle_eligibility(profile: UserProfile, message: str, language: str, session: dict) -> dict:
    slot = get_next_slot(profile, session["skipped_slots"])
    session["last_slot_asked"] = slot
    if slot is not None:
        return {
            "answer": translate(_slot_prompt(session, slot), source_lang="en", target_lang=language),
            "sources": [],
            "confidence": "medium",
            "eligibility_results": [],
        }

    # Search with the original question, not the last slot reply ("female"). Cleared once used.
    stored_query = session.get("eligibility_query") or message
    no_topic = not _has_topic(stored_query)
    if no_topic:
        search_query, used = _profile_search_query(profile)
    else:
        search_query = stored_query
    session["eligibility_query"] = None
    session["last_slot_asked"] = None
    candidates = retrieve(search_query, top_k=3)
    if not candidates:
        return {
            "answer": translate(
                "I couldn't find a matching scheme to check eligibility against. "
                "Please check myscheme.gov.in.",
                source_lang="en",
                target_lang=language,
            ),
            "sources": [],
            "confidence": "low",
            "eligibility_results": [],
        }

    lines = []
    sources = []
    eligibility_results = []
    any_unverifiable = False
    seen_schemes = set()
    for hit in candidates:
        scheme_name = hit["scheme_name"]
        if scheme_name in seen_schemes:
            continue
        seen_schemes.add(scheme_name)

        result = check_eligibility(profile, hit["scheme"])
        unverifiable = [u for u in result["unverifiable_conditions"] if not _is_junk(u)]
        if unverifiable:
            any_unverifiable = True

        if result["eligible"]:
            lines.append(f"You appear to be ELIGIBLE for {scheme_name}.")
            reasons = []
        else:
            reasons = result["failed_conditions"] or ["some conditions are not met"]
            lines.append(f"You do NOT appear to be eligible for {scheme_name} ({'; '.join(reasons)}).")

        if unverifiable:
            lines.append(
                f"Some conditions for {scheme_name} could not be verified automatically: "
                + "; ".join(unverifiable)
            )

        eligibility_results.append(
            {
                "scheme_name": scheme_name,
                "eligible": result["eligible"],
                "reasons": reasons + unverifiable,
            }
        )

        sources.append(
            {"scheme_name": scheme_name, "section": "eligibility", "source_file": hit["source_file"]}
        )

    if no_topic:
        lines.insert(0, NO_TOPIC_NOTE.format(profile=used))
    answer_text = " ".join(lines)
    confidence = "medium" if any_unverifiable else "high"

    return {
        "answer": translate(
            answer_text,
            source_lang="en",
            target_lang=language,
            schemes=[src.get("scheme_name", "") for src in sources],
        ),
        "sources": sources,
        "confidence": confidence,
        "eligibility_results": eligibility_results,
    }


def _format_data_as_of(value) -> str:
    return f"Data as of {value.strftime('%d %b %Y')}"


def _add_sync_dates(sources: list) -> None:
    """Attach last_synced / data_as_of to each cited source that has a sync date in MongoDB."""
    files = list({s["source_file"] for s in sources if s.get("source_file")})
    if not files:
        return
    try:
        synced = {
            doc["source_file"]: doc["last_synced"]
            for doc in get_schemes_collection().find(
                {"source_file": {"$in": files}, "last_synced": {"$exists": True}},
                {"source_file": 1, "last_synced": 1},
            )
            if isinstance(doc.get("last_synced"), datetime)
        }
    except Exception:
        logger.exception("failed to look up last_synced for sources")
        return
    for source in sources:
        last_synced = synced.get(source.get("source_file"))
        if last_synced:
            last_synced = last_synced.replace(tzinfo=timezone.utc) if last_synced.tzinfo is None else last_synced
            source["last_synced"] = last_synced.isoformat()
            source["data_as_of"] = _format_data_as_of(last_synced)


def _process_message(message: str, session_id: Optional[str], language_override: Optional[str]) -> dict:
    if len(message) > MAX_MESSAGE_LENGTH:
        raise HTTPException(status_code=400, detail="Message exceeds 1000 character limit.")

    if _contains_injection(message):
        sid, _ = _get_session(session_id)
        return {
            "answer": INJECTION_DECLINE_MESSAGE,
            "sources": [],
            "confidence": "low",
            "intent": "out_of_scope",
            "language": "en",
            "session_id": sid,
        }

    language = language_override or detect_language(message)
    sid, session = _get_session(session_id)
    profile: UserProfile = session["profile"]

    # intent_classifier is English-only regex matching; translate non-English
    # queries inward for classification purposes. Retrieval and generation
    # still use the original-language `message` — multilingual-e5-small
    # embeds Tamil/Hindi/English natively, so translating for retrieval would
    # only lose signal.
    classification_query = message if language == "en" else translate(message, source_lang=language, target_lang="en")

    # translate() returns the original text unchanged when no model is
    # installed for this language pair (e.g. Tamil has none). A non-Latin
    # query that comes back untranslated would otherwise hit the
    # English-only classifier verbatim and fail — default it to
    # scheme_search instead, which is the overwhelmingly common intent for
    # untranslatable non-English queries on this platform.
    # Native-script keyword pre-check runs on the original text, before
    # trusting the translation.
    native = classify(message) if language != "en" else None
    if native and native["intent"] != "out_of_scope":
        intent = native["intent"]
        entities = native["extracted_entities"]
    elif _is_translation_failed(message, classification_query, language):
        intent = "scheme_search"
        entities = {}
    else:
        classification = classify(classification_query)
        intent = classification["intent"]
        entities = classification["extracted_entities"]

    # A plain slot-filling answer ("I am 30 years old") has no intent
    # trigger phrases and would otherwise fall to out_of_scope. If the bot's
    # previous message was an eligibility slot-filling question, treat this
    # message as a continuation of that flow regardless of what the
    # classifier says.
    # The slot being asked is interpreted from the (English) reply; entities from the
    # full sentence are applied first so "I am female" still fills gender.
    _apply_entities(profile, entities)
    asked_slot = session.get("last_slot_asked")
    topic_change = asked_slot is not None and bool(TOPIC_CHANGE_RE.match(classification_query))
    if topic_change:
        # "actually, for education" swaps the topic and keeps the flow; it is not a slot answer.
        session["eligibility_query"] = _topic_change_query(classification_query)
        intent = "eligibility_check"
    elif asked_slot is not None and intent in ("out_of_scope", "eligibility_check"):
        if intent == "eligibility_check":  # a fresh eligibility question replaces the stored one
            session["eligibility_query"] = message
            session["slot_failures"] = {}
        else:
            _fill_asked_slot(session, profile, classification_query)
            intent = "eligibility_check"  # a bare "general" / "30" carries no intent of its own
    elif intent == "eligibility_check":
        session["eligibility_query"] = message
        session["slot_failures"] = {}
        session["skipped_slots"] = set()
    elif session.get("last_intent") == "eligibility_check" and session.get("last_bot_message_was_question"):
        intent = "eligibility_check"

    eligibility_results = []
    if intent == "scheme_search" or intent == "comparison":
        suffix = COMPARISON_PROMPT_ADDITION if intent == "comparison" else ""
        result = rag_answer(message, language=language, system_prompt_suffix=suffix)
        answer_text, sources, confidence = result["answer"], result["sources"], result["confidence"]
    elif intent == "eligibility_check":
        result = _handle_eligibility(profile, message, language, session)
        answer_text, sources, confidence = result["answer"], result["sources"], result["confidence"]
        eligibility_results = result["eligibility_results"]
    elif intent == "document_upload":
        answer_text = translate(DOCUMENT_UPLOAD_PROMPT, source_lang="en", target_lang=language)
        sources, confidence = [], "medium"
    else:
        answer_text = translate(OUT_OF_SCOPE_MESSAGE, source_lang="en", target_lang=language)
        sources, confidence = [], "low"

    if language != "en":
        answer_text = _strip_stray_asterisks(answer_text)

    if intent != "eligibility_check":
        session["last_slot_asked"] = None  # flow abandoned; don't hijack the next reply
    _add_sync_dates(sources)

    session["history"].append({"role": "user", "message": message})
    session["history"].append({"role": "assistant", "message": answer_text})
    session["last_intent"] = intent
    session["last_bot_message_was_question"] = answer_text.rstrip().endswith("?")

    return {
        "answer": answer_text,
        "sources": sources,
        "confidence": confidence,
        "intent": intent,
        "language": language,
        "session_id": sid,
        "profile": profile.model_dump(),
        "eligibility_results": eligibility_results,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    try:
        schemes_loaded = get_schemes_collection().count_documents({})
    except Exception:
        logger.exception("health: failed to count MongoDB documents")
        schemes_loaded = 0

    try:
        import chromadb

        client = chromadb.PersistentClient(path=settings.chroma_persist_path)
        collection = client.get_or_create_collection(CHROMA_COLLECTION_NAME)
        embeddings_loaded = collection.count()
    except Exception:
        logger.exception("health: failed to count ChromaDB embeddings")
        embeddings_loaded = 0

    return {"status": "ok", "schemes_loaded": schemes_loaded, "embeddings_loaded": embeddings_loaded}


@app.get("/sync/status")
def sync_status_endpoint():
    status = sync_status.get_sync_status()
    try:
        total_schemes = get_schemes_collection().count_documents({})
    except Exception:
        logger.exception("sync/status: failed to count MongoDB documents")
        total_schemes = 0

    if settings.sync_scheduler_enabled:
        next_run = sync_scheduler.get_next_run_time() or sync_scheduler.next_default_run()
    else:
        next_run = None

    return {
        "last_sync": status["last_sync"],
        "schemes_updated_last_sync": status["schemes_updated_last_sync"],
        "total_schemes": total_schemes,
        "next_scheduled_sync": next_run.isoformat(timespec="seconds") if next_run else None,
        "sync_in_progress": status["sync_in_progress"],
        "last_sync_failed": status["last_sync_failed"],
    }


@app.get("/sync/trigger")
def sync_trigger(x_api_key: Optional[str] = Header(None)):
    # Header (not query string) so the key doesn't end up in access logs.
    if not settings.sync_api_key:
        raise HTTPException(status_code=503, detail="Sync trigger is disabled: SYNC_API_KEY is not set.")
    if not x_api_key or not hmac.compare_digest(x_api_key, settings.sync_api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")
    if sync_status.is_sync_running():
        raise HTTPException(status_code=409, detail="A sync is already running.")
    sync_scheduler.trigger_sync_in_background()
    return {"status": "sync started", "check": "/sync/status"}


@app.post("/feedback")
def feedback(request: FeedbackRequest):
    # One vote per (session, message): re-sending overwrites rather than duplicating.
    try:
        get_db()["feedback"].update_one(
            {"session_id": request.session_id, "message_index": request.message_index},
            {
                "$set": {
                    "rating": request.rating,
                    "query": request.query[:MAX_MESSAGE_LENGTH],
                    "intent": request.intent,
                    "updated_at": datetime.now(timezone.utc),
                },
                "$setOnInsert": {"created_at": datetime.now(timezone.utc)},
            },
            upsert=True,
        )
    except Exception:
        logger.exception("feedback: failed to store feedback")
        raise HTTPException(status_code=503, detail="Could not store feedback right now.")
    return {"status": "ok"}


@app.post("/profile", response_model=ProfileResponse)
def update_profile(request: ProfileRequest):
    sid, session = _get_session(request.session_id)
    session["profile"] = request.profile
    return ProfileResponse(session_id=sid, profile=request.profile)


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    result = _process_message(request.message, request.session_id, request.language)
    return ChatResponse(**result)


@app.post("/document/upload")
async def upload_document(file: UploadFile = File(...), session_id: Optional[str] = Form(None)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    sid, session = _get_session(session_id)

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        ocr_result = extract_text(tmp_path)
        extracted = extract_fields(ocr_result["text"])
        fill_result = autofill_profile(extracted, session["profile"])
        session["profile"] = fill_result["updated_profile"]
    finally:
        import os

        os.unlink(tmp_path)

    return {
        "session_id": sid,
        "fields": extracted["fields"].model_dump(),
        "confidence": extracted["confidence"],
        "profile": fill_result["updated_profile"].model_dump(),
        "high_confidence_fills": fill_result["high_confidence_fills"],
        "needs_confirmation": fill_result["needs_confirmation"],
        "failed_fields": fill_result["failed_fields"],
    }


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            session_id = data.get("session_id")
            language = data.get("language")

            try:
                if session_id:
                    async with _ws_session_locks.setdefault(session_id, asyncio.Lock()):
                        result = await run_in_threadpool(_process_message, message, session_id, language)
                else:
                    result = await run_in_threadpool(_process_message, message, session_id, language)
            except HTTPException as exc:
                await websocket.send_json({"error": exc.detail})
                continue

            await websocket.send_json(result)
    except WebSocketDisconnect:
        logger.info("websocket_chat: client disconnected")
    finally:
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close()
