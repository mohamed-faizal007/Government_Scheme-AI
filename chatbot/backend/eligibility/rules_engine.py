"""Deterministic eligibility rules engine. Never guesses — any condition it cannot
parse with confidence goes to unverifiable_conditions instead of being scored.
Run test: python -m chatbot.backend.eligibility.rules_engine  (from repo root)
"""
import re

from ..database.load_chroma import STATE_NAMES
from .user_profile import UserProfile

CATEGORY_KEYWORDS = {
    "sc": r"\bsc\b|scheduled caste",
    "st": r"\bst\b|scheduled tribe",
    "obc": r"\bobc\b|other backward class",
    "general": r"\bgeneral category\b",
    "women": r"\bwomen\b|\bwoman\b|\bfemale\b",
    "differently abled": r"differently abled|\bdisability\b|\bpwd\b",
    "ex-serviceman": r"ex-?servicem[ae]n",
}

# Words that flip a state/category match into its opposite (e.g. "non-resident",
# "not eligible", "other than") — numeric age/income comparisons don't need this
# since their direction is already encoded in the comparison word itself.
NEGATION_PATTERN = r"\bnon-?resident|non-?[a-z]+|\bnot\s+(?:a|an|be|residing|listed|associated|eligible)|other than|outside|excluding"

_AMOUNT_UNITS = {"lakh": 100_000, "lakhs": 100_000, "crore": 10_000_000, "crores": 10_000_000}


def _to_amount(number_str: str, unit: str | None) -> float:
    value = float(number_str.replace(",", ""))
    return value * _AMOUNT_UNITS.get((unit or "").lower(), 1)


_NON_THRESHOLD_PATTERN = r"\bpriority\b|\bpreference\b|\bnote\b|\badditional\b|\bweightage\b"

_MAX_REASON_LEN = 120

_JUNK_PUNCT_ONLY = re.compile(r"^[\s\W_]+$")


def _truncate(text: str) -> str:
    if len(text) > _MAX_REASON_LEN:
        return text[:_MAX_REASON_LEN] + "..."
    return text


def _is_junk(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 10:
        return True
    if _JUNK_PUNCT_ONLY.match(stripped):
        return True
    if stripped.endswith("?"):
        body = stripped.rstrip("?").strip()
        # Fragments like "also applicable ?" have real words but no substance —
        # too few words to be a genuine question or condition.
        if len(body) < 10 or len(body.split()) < 3:
            return True
    return False


def _check_age(text: str, age: int | None) -> str | None:
    t = text.lower()
    if re.search(_NON_THRESHOLD_PATTERN, t):
        return None
    m = re.search(r"between\s*(\d+)\s*(?:and|-)\s*(\d+)\s*years?", t)
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        return None if age is None else ("pass" if lo <= age <= hi else "fail")
    m = re.search(r"not\s*exceeding\s*(\d+)\s*years?", t)
    if m:
        x = int(m.group(1))
        return "unverifiable" if age is None else ("pass" if age <= x else "fail")
    m = re.search(r"minimum\s*age(?:\s*of)?\s*(\d+)", t)
    if m:
        x = int(m.group(1))
        return "unverifiable" if age is None else ("pass" if age >= x else "fail")
    m = re.search(r"below\s*(\d+)\s*years?", t)
    if m:
        x = int(m.group(1))
        return "unverifiable" if age is None else ("pass" if age < x else "fail")
    m = re.search(r"above\s*(\d+)\s*years?", t)
    if m:
        x = int(m.group(1))
        return "unverifiable" if age is None else ("pass" if age > x else "fail")
    if re.search(r"\bage\b", t):
        return "unverifiable"
    return None


def _check_income(text: str, income: float | None) -> str | None:
    t = text.lower()
    if re.search(r"\bbpl\b|\bapl\b", t):
        return "unverifiable"  # no explicit numeric threshold given — never guess

    # Currency symbol/unit is required (not optional) so bare numbers in unrelated
    # clauses (e.g. "above 21 years of age") never get misread as income amounts.
    m = re.search(
        r"(?:exceeding|more than|above)\s*(?:rs\.?|₹)\s*([\d,]+(?:\.\d+)?)\s*(lakh|lakhs|crore|crores)?"
        r"|(?:exceeding|more than|above)\s*([\d,]+(?:\.\d+)?)\s*(lakh|lakhs|crore|crores)",
        t,
    )
    if m:
        number = m.group(1) or m.group(3)
        unit = m.group(2) or m.group(4)
        value = _to_amount(number, unit)
        return "unverifiable" if income is None else ("pass" if income <= value else "fail")

    below_keywords = r"less than|below|not exceeding|(?:shall|should|does|do)\s+not\s+exceed|up to"
    m = re.search(
        rf"(?:{below_keywords})\s*(?:rs\.?|₹)\s*([\d,]+(?:\.\d+)?)\s*(lakh|lakhs|crore|crores)?"
        rf"|(?:{below_keywords})\s*([\d,]+(?:\.\d+)?)\s*(lakh|lakhs|crore|crores)",
        t,
    )
    if m:
        number = m.group(1) or m.group(3)
        unit = m.group(2) or m.group(4)
        value = _to_amount(number, unit)
        return "unverifiable" if income is None else ("pass" if income <= value else "fail")

    if re.search(r"\bincome\b", t):
        return "unverifiable"
    return None


def _check_category(text: str, profile: UserProfile) -> str | None:
    t = text.lower()
    for category, pattern in CATEGORY_KEYWORDS.items():
        if not re.search(pattern, t, re.IGNORECASE):
            continue
        negated = bool(re.search(NEGATION_PATTERN, t, re.IGNORECASE))
        if category == "women":
            if profile.gender is None:
                return "unverifiable"
            matches = profile.gender.lower() == "female"
        elif category == "differently abled":
            if profile.disability is None:
                return "unverifiable"
            matches = profile.disability is True
        elif category == "ex-serviceman":
            if profile.is_ex_serviceman is None:
                return "unverifiable"
            matches = profile.is_ex_serviceman is True
        else:
            if profile.category is None:
                return "unverifiable"
            matches = profile.category.lower() == category
        return "pass" if (matches != negated) else "fail"
    return None


def _check_state(text: str, profile: UserProfile) -> str | None:
    for state in STATE_NAMES:
        if state.lower() in text.lower():
            negated = bool(re.search(NEGATION_PATTERN, text, re.IGNORECASE))
            if profile.state is None:
                return "unverifiable"
            matches = profile.state.lower() == state.lower()
            return "pass" if (matches != negated) else "fail"
    return None


def _evaluate(text: str, profile: UserProfile) -> str:
    results = []
    for checker, value in ((_check_age, profile.age), (_check_income, profile.income_annual)):
        result = checker(text, value)
        if result is not None:
            results.append(result)

    result = _check_category(text, profile)
    if result is not None:
        results.append(result)

    result = _check_state(text, profile)
    if result is not None:
        results.append(result)

    if not results:
        return "unverifiable"
    if "fail" in results:
        return "fail"
    if "unverifiable" in results:
        return "unverifiable"
    return "pass"


def check_eligibility(profile: UserProfile, scheme: dict) -> dict:
    eligibility = scheme.get("eligibility", {}) or {}
    conditions = eligibility.get("conditions", []) or []
    exclusions = eligibility.get("exclusions", []) or []

    reasons = []
    failed_conditions = []
    unverifiable_conditions = []
    eligible = True

    for condition in conditions:
        result = _evaluate(condition, profile)
        if result == "pass":
            reasons.append(_truncate(f"Meets condition: {condition}"))
        elif result == "fail":
            failed_conditions.append(_truncate(condition))
            eligible = False
        else:
            unverifiable_conditions.append(condition)

    for exclusion in exclusions:
        result = _evaluate(exclusion, profile)
        if result == "pass":
            failed_conditions.append(_truncate(f"Excluded: {exclusion}"))
            eligible = False
        elif result == "unverifiable":
            unverifiable_conditions.append(exclusion)

    reasons = [r for r in reasons if not _is_junk(r)]
    failed_conditions = [f for f in failed_conditions if not _is_junk(f)]

    return {
        "eligible": eligible,
        "reasons": reasons,
        "failed_conditions": failed_conditions,
        "unverifiable_conditions": unverifiable_conditions,
    }


if __name__ == "__main__":
    import json
    import sys

    sys.stdout.reconfigure(encoding="utf-8")

    profile = UserProfile(
        age=30,
        gender="male",
        state="Tamil Nadu",
        income_annual=120_000,
        category="sc",
        disability=False,
        is_ex_serviceman=False,
    )

    test_files = [
        "aabcs copy.json",
        "aaelss copy.json",
        "aaas-assam copy.json",
    ]

    for fname in test_files:
        path = f"dataset/gov_myscheme/test_output_unstructured/{fname}"
        with open(path, encoding="utf-8") as f:
            scheme = json.load(f)

        result = check_eligibility(profile, scheme)
        print(f"\n=== {scheme['metadata']['scheme_name']} ({fname}) ===")
        print(json.dumps(result, indent=2, ensure_ascii=False))
