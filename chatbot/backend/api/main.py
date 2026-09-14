"""FastAPI backend — chat, profile, health, and WebSocket endpoints.
Run: uvicorn chatbot.backend.api.main:app --reload --port 8000  (from repo root)
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.websockets import WebSocketState

from ..database.load_chroma import COLLECTION_NAME as CHROMA_COLLECTION_NAME
from ..database.mongo_client import get_schemes_collection
from ..eligibility.rules_engine import check_eligibility
from ..eligibility.slot_filler import get_next_question
from ..eligibility.user_profile import UserProfile
from ..rag.rag_chain import answer as rag_answer
from ..retrieval.retriever import retrieve
from ..router.intent_classifier import classify
from ..translation.translator import detect_language, translate

logger = logging.getLogger(__name__)

app = FastAPI(title="Government Scheme AI Chatbot")

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

DOCUMENT_UPLOAD_PROMPT = (
    "Please upload your document (PDF) using the file upload option so I can "
    "verify it and help fill in your profile."
)

_sessions: dict[str, dict] = {}


def _new_session() -> dict:
    return {
        "profile": UserProfile(),
        "history": [],
        "last_active": datetime.now(timezone.utc),
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
}


def _apply_entities(profile: UserProfile, entities: dict) -> None:
    for entity_key, profile_field in ENTITY_TO_PROFILE_FIELD.items():
        if entity_key in entities:
            setattr(profile, profile_field, entities[entity_key])


def _handle_eligibility(profile: UserProfile, message: str, language: str) -> dict:
    next_question = get_next_question(profile)
    if next_question is not None:
        return {
            "answer": translate(next_question, source_lang="en", target_lang=language),
            "sources": [],
            "confidence": "medium",
        }

    candidates = retrieve(message, top_k=3)
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
        }

    lines = []
    sources = []
    any_unverifiable = False
    seen_schemes = set()
    for hit in candidates:
        scheme_name = hit["scheme_name"]
        if scheme_name in seen_schemes:
            continue
        seen_schemes.add(scheme_name)

        result = check_eligibility(profile, hit["scheme"])
        if result["unverifiable_conditions"]:
            any_unverifiable = True

        if result["eligible"]:
            lines.append(f"You appear to be ELIGIBLE for {scheme_name}.")
        else:
            reasons = "; ".join(result["failed_conditions"]) or "some conditions are not met"
            lines.append(f"You do NOT appear to be eligible for {scheme_name} ({reasons}).")

        if result["unverifiable_conditions"]:
            lines.append(
                f"Some conditions for {scheme_name} could not be verified automatically: "
                + "; ".join(result["unverifiable_conditions"])
            )

        sources.append(
            {"scheme_name": scheme_name, "section": "eligibility", "source_file": hit["source_file"]}
        )

    answer_text = " ".join(lines)
    confidence = "medium" if any_unverifiable else "high"

    return {
        "answer": translate(answer_text, source_lang="en", target_lang=language),
        "sources": sources,
        "confidence": confidence,
    }


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
    classification = classify(classification_query)
    intent = classification["intent"]
    _apply_entities(profile, classification["extracted_entities"])

    if intent == "scheme_search" or intent == "comparison":
        result = rag_answer(message, language=language)
        answer_text, sources, confidence = result["answer"], result["sources"], result["confidence"]
    elif intent == "eligibility_check":
        result = _handle_eligibility(profile, message, language)
        answer_text, sources, confidence = result["answer"], result["sources"], result["confidence"]
    elif intent == "document_upload":
        answer_text = translate(DOCUMENT_UPLOAD_PROMPT, source_lang="en", target_lang=language)
        sources, confidence = [], "medium"
    else:
        answer_text = translate(OUT_OF_SCOPE_MESSAGE, source_lang="en", target_lang=language)
        sources, confidence = [], "low"

    session["history"].append({"role": "user", "message": message})
    session["history"].append({"role": "assistant", "message": answer_text})

    return {
        "answer": answer_text,
        "sources": sources,
        "confidence": confidence,
        "intent": intent,
        "language": language,
        "session_id": sid,
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

        from ..config import settings

        client = chromadb.PersistentClient(path=settings.chroma_persist_path)
        collection = client.get_or_create_collection(CHROMA_COLLECTION_NAME)
        embeddings_loaded = collection.count()
    except Exception:
        logger.exception("health: failed to count ChromaDB embeddings")
        embeddings_loaded = 0

    return {"status": "ok", "schemes_loaded": schemes_loaded, "embeddings_loaded": embeddings_loaded}


@app.post("/profile", response_model=ProfileResponse)
def update_profile(request: ProfileRequest):
    sid, session = _get_session(request.session_id)
    session["profile"] = request.profile
    return ProfileResponse(session_id=sid, profile=request.profile)


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    result = _process_message(request.message, request.session_id, request.language)
    return ChatResponse(**result)


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
                result = _process_message(message, session_id, language)
            except HTTPException as exc:
                await websocket.send_json({"error": exc.detail})
                continue

            await websocket.send_json(result)
    except WebSocketDisconnect:
        logger.info("websocket_chat: client disconnected")
    finally:
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close()
