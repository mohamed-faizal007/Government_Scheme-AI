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
    "aadhaar_last4",
]


class DocumentFields(BaseModel):
    name: Optional[str] = None
    date_of_birth: Optional[str] = None
    age: Optional[int] = None
    income_annual: Optional[float] = None
    category: Optional[str] = None
    state: Optional[str] = None
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
    aadhaar_last4: Optional[str] = Field(
        None, description="ONLY the last 4 digits of any Aadhaar number found. Never the full 12-digit number."
    )
    aadhaar_last4_confidence: float = Field(0.0, ge=0.0, le=1.0)


SYSTEM_PROMPT = """You extract structured fields from Indian government document text
(income certificates, caste certificates, ID proofs, etc).

Rules:
- Extract only what is explicitly present in the text. Do not guess or infer missing values.
- category must be normalized to one of: general, obc, sc, st (lowercase) when a caste/category is stated.
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

    fields = DocumentFields(
        name=result.name,
        date_of_birth=result.date_of_birth,
        age=result.age,
        income_annual=result.income_annual,
        category=result.category,
        state=result.state,
        aadhaar_last4=masked_aadhaar,
    )
    confidence = {
        "name": result.name_confidence,
        "date_of_birth": result.date_of_birth_confidence,
        "age": result.age_confidence,
        "income_annual": result.income_annual_confidence,
        "category": result.category_confidence,
        "state": result.state_confidence,
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
    }

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
