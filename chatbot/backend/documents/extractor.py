"""Structured field extraction from OCR'd document text, using Groq + Instructor.

SECURITY: a full 12-digit Aadhaar number must never be stored, logged, or
returned. The LLM is instructed to return only the last 4 digits, and
`_mask_aadhaar` re-masks whatever comes back as a hard backstop before it
touches a return value or a log line.

Run test: python -m chatbot.backend.documents.extractor  (from repo root)
"""
import logging
import re
from typing import Optional

import instructor
from groq import Groq
from pydantic import BaseModel, Field

from ..config import settings
from ..eligibility.user_profile import UserProfile

logger = logging.getLogger(__name__)

HIGH_CONFIDENCE = 0.85
LOW_CONFIDENCE = 0.50

FIELD_NAMES = [
    "name",
    "date_of_birth",
    "age",
    "income_annual",
    "category",
    "state",
    "gender",
    "occupation",
    "aadhaar_last4",
]


class DocumentFields(BaseModel):
    name: Optional[str] = None
    date_of_birth: Optional[str] = None
    age: Optional[int] = None
    income_annual: Optional[float] = None
    category: Optional[str] = None
    state: Optional[str] = None
    gender: Optional[str] = None
    occupation: Optional[str] = None
    aadhaar_last4: Optional[str] = None  # last 4 digits ONLY


class _ExtractionResult(BaseModel):
    """Internal Instructor response model — DocumentFields with a confidence
    score alongside each field. Never exposed outside this module."""

    name: Optional[str] = None
    name_confidence: float = Field(0.0, ge=0.0, le=1.0)
    date_of_birth: Optional[str] = None
    date_of_birth_confidence: float = Field(0.0, ge=0.0, le=1.0)
    age: Optional[int] = None
    age_confidence: float = Field(0.0, ge=0.0, le=1.0)
    income_annual: Optional[float] = None
    income_annual_confidence: float = Field(0.0, ge=0.0, le=1.0)
    category: Optional[str] = None
    category_confidence: float = Field(0.0, ge=0.0, le=1.0)
    state: Optional[str] = None
    state_confidence: float = Field(0.0, ge=0.0, le=1.0)
    gender: Optional[str] = None
    gender_confidence: float = Field(0.0, ge=0.0, le=1.0)
    occupation: Optional[str] = None
    occupation_confidence: float = Field(0.0, ge=0.0, le=1.0)
    aadhaar_last4: Optional[str] = Field(
        None, description="ONLY the last 4 digits of any Aadhaar number found. Never the full 12-digit number."
    )
    aadhaar_last4_confidence: float = Field(0.0, ge=0.0, le=1.0)


SYSTEM_PROMPT = """You extract structured fields from Indian government document text
(income certificates, caste certificates, ID proofs, etc).

Rules:
- Extract only what is explicitly present in the text. Do not guess or infer missing values.
- category must be normalized to one of: general, obc, sc, st (lowercase) when a caste/category is stated.
- gender must be one of: male, female, other, and only when the document states it (a "Sex"/"Gender" field, or
  words such as "S/O", "D/O", "W/O", "Mr", "Mrs", "Smt").
- occupation is a short lowercase noun such as farmer, student, labourer, only when the document states it.
- income_annual must be a plain number in rupees (convert "1,80,000" -> 180000, "1.5 lakh" -> 150000).
- If an Aadhaar number appears, return ONLY its last 4 digits in aadhaar_last4. NEVER return the full number.
- For every field, also give a confidence score from 0.0 to 1.0 reflecting how certain you are the value is
  correct and unambiguous in the source text. Use 0.0 confidence and null value for anything not found."""


def _mask_aadhaar(value: str | None) -> str | None:
    """Hard backstop: keep only the last 4 digits, no matter what the LLM returned."""
    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    return digits[-4:] if digits else None


# --- normalisation and grounding -------------------------------------------------------------
# The profile's category values are the ones the rules engine and scheme data use: general, obc, sc, st.
_CATEGORY_SYNONYMS = [
    ("sc", r"^(?:sc|scheduled\s+castes?)$"),
    ("st", r"^(?:st|scheduled\s+tribes?)$"),
    ("obc", r"^(?:obc|bc|mbc|other\s+backward\s+class(?:es)?|backward\s+class(?:es)?|most\s+backward\s+class(?:es)?)$"),
    ("general", r"^(?:general|gen|oc|open|unreserved|general\s+category)$"),
]
_CATEGORY_EVIDENCE = {
    "sc": r"\bsc\b|scheduled\s+castes?",
    "st": r"\bst\b|scheduled\s+tribes?",
    "obc": r"\bobc\b|\bm?bc\b|other\s+backward|backward\s+class",
    "general": r"(?:category|caste|community|class)\s*[:\-]?\s*(?:general|gen|oc|open|unreserved)\b|general\s+category|unreserved",
}
_GENDER_VALUES = [
    ("female", r"^(?:f|female|woman|women|girl)$"),
    ("male", r"^(?:m|male|man|boy)$"),
    ("other", r"^(?:other|transgender|third\s+gender|non[- ]?binary)$"),
]
_GENDER_EVIDENCE = {
    "female": r"\bfemale\b|\bwoman\b|\bd/o\b|\bw/o\b|daughter\s+of|wife\s+of|\bmrs\b|\bmiss\b|\bsmt\b|\bkumari\b|"
              r"(?:sex|gender)\s*[:/\-]?\s*(?:f|female)\b",
    "male": r"(?<![a-z])male\b|\bs/o\b|son\s+of|\bmr\b|\bshri\b|(?:sex|gender)\s*[:/\-]?\s*(?:m|male)\b",
    "other": r"transgender|third\s+gender|\bother\b",
}


def _normalize(value: str | None, table: list[tuple[str, str]]) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r"[.\s]+", " ", value.strip().lower()).strip()
    return next((name for name, pattern in table if re.match(pattern, cleaned)), None)


def _normalize_occupation(value: str | None) -> str | None:
    cleaned = re.sub(r"\s+", " ", (value or "").strip().lower())
    return cleaned[:40] if cleaned else None


def _grounded(field: str, value, text: str) -> bool:
    """True when the document text itself supports `value`; a model's guess is never enough."""
    if field == "category":
        return bool(re.search(_CATEGORY_EVIDENCE[value], text, re.IGNORECASE))
    if field == "gender":
        return bool(re.search(_GENDER_EVIDENCE[value], text, re.IGNORECASE))
    if field == "occupation":
        words = [w for w in re.findall(r"[a-z]+", value) if len(w) >= 4]
        return any(w in text.lower() for w in words)
    return True


def _get_client():
    return instructor.from_groq(Groq(api_key=settings.groq_api_key), mode=instructor.Mode.JSON)


def extract_fields(text: str) -> dict:
    client = _get_client()

    result: _ExtractionResult = client.chat.completions.create(
        model=settings.groq_model,
        response_model=_ExtractionResult,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
    )

    masked_aadhaar = _mask_aadhaar(result.aadhaar_last4)

    normalized = {
        "category": _normalize(result.category, _CATEGORY_SYNONYMS),
        "gender": _normalize(result.gender, _GENDER_VALUES),
        "occupation": _normalize_occupation(result.occupation),
    }
    scores = {
        "category": result.category_confidence,
        "gender": result.gender_confidence,
        "occupation": result.occupation_confidence,
    }
    for field, value in normalized.items():
        if value is not None and not _grounded(field, value, text):
            logger.info("document_field_dropped_ungrounded field=%s", field)
            normalized[field] = None
        if normalized[field] is None:
            scores[field] = 0.0

    fields = DocumentFields(
        name=result.name,
        date_of_birth=result.date_of_birth,
        age=result.age,
        income_annual=result.income_annual,
        category=normalized["category"],
        state=result.state,
        gender=normalized["gender"],
        occupation=normalized["occupation"],
        aadhaar_last4=masked_aadhaar,
    )
    confidence = {
        "name": result.name_confidence,
        "date_of_birth": result.date_of_birth_confidence,
        "age": result.age_confidence,
        "income_annual": result.income_annual_confidence,
        "category": scores["category"],
        "state": result.state_confidence,
        "gender": scores["gender"],
        "occupation": scores["occupation"],
        "aadhaar_last4": result.aadhaar_last4_confidence,
    }

    logger.info(
        "document_fields_extracted fields=%s aadhaar_present=%s",
        [f for f in FIELD_NAMES if getattr(fields, f) is not None],
        masked_aadhaar is not None,
    )

    return {"fields": fields, "confidence": confidence}


def autofill_profile(extracted: dict, profile: UserProfile) -> dict:
    fields: DocumentFields = extracted["fields"]
    confidence: dict = extracted["confidence"]

    updated = profile.model_copy()
    high_confidence_fills = []
    needs_confirmation = []
    failed_fields = []

    profile_field_map = {
        "age": "age",
        "income_annual": "income_annual",
        "category": "category",
        "state": "state",
        "gender": "gender",
        "occupation": "occupation",
    }

    # A field the document lacks is left exactly as it was: uploads may overwrite what they contain, never invent.
    for doc_field, profile_field in profile_field_map.items():
        value = getattr(fields, doc_field)
        score = confidence.get(doc_field, 0.0)

        if value is None:
            failed_fields.append(doc_field)
            continue

        if score >= HIGH_CONFIDENCE:
            setattr(updated, profile_field, value)
            high_confidence_fills.append(doc_field)
        elif score >= LOW_CONFIDENCE:
            setattr(updated, profile_field, value)
            needs_confirmation.append(doc_field)
        else:
            failed_fields.append(doc_field)

    return {
        "updated_profile": updated,
        "high_confidence_fills": high_confidence_fills,
        "needs_confirmation": needs_confirmation,
        "failed_fields": failed_fields,
    }


if __name__ == "__main__":
    import json
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO)

    sample_text = """INCOME CERTIFICATE
Name: Rajesh Kumar
Date of Birth: 15/03/1990
Annual Income: Rs. 1,80,000
Caste: OBC
State: Tamil Nadu"""

    extracted = extract_fields(sample_text)
    print("\n=== extract_fields ===")
    print(json.dumps({"fields": extracted["fields"].model_dump(), "confidence": extracted["confidence"]}, indent=2))

    profile = UserProfile()
    result = autofill_profile(extracted, profile)
    print("\n=== autofill_profile ===")
    print(
        json.dumps(
            {
                "updated_profile": result["updated_profile"].model_dump(),
                "high_confidence_fills": result["high_confidence_fills"],
                "needs_confirmation": result["needs_confirmation"],
                "failed_fields": result["failed_fields"],
            },
            indent=2,
        )
    )
