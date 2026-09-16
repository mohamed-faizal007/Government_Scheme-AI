"""Phase 10 eligibility engine evaluation: 20 manually-defined (UserProfile, scheme,
expected_eligible) test cases against real schemes from
dataset/gov_myscheme/test_output_unstructured/. Reports accuracy % and how many
cases surfaced at least one unverifiable condition (not counted as a failure --
expected for ambiguous rule text).

Run: python -m chatbot.evaluation.eval_eligibility  (from repo root)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from chatbot.backend.eligibility.rules_engine import check_eligibility
from chatbot.backend.eligibility.user_profile import UserProfile

DATASET_DIR = Path(__file__).resolve().parent.parent.parent / "dataset" / "gov_myscheme" / "test_output_unstructured"


def _load(fname: str) -> dict:
    with open(DATASET_DIR / fname, encoding="utf-8") as f:
        return json.load(f)


# Each case: (description, scheme_file, profile, expected_eligible)
TEST_CASES = [
    (
        "Assam resident, income 3L -> eligible for Assam Arogya Nidhi",
        "aan copy.json",
        UserProfile(age=40, state="Assam", income_annual=300_000),
        True,
    ),
    (
        "Bihar resident (not Assam) -> NOT eligible for Assam Arogya Nidhi",
        "aan copy.json",
        UserProfile(age=40, state="Bihar", income_annual=300_000),
        False,
    ),
    (
        "Age 30 within 18-60 -> eligible for Agri-Clinics scheme",
        "acandabc copy.json",
        UserProfile(age=30),
        True,
    ),
    (
        "Age 65 exceeds 18-60 window -> NOT eligible for Agri-Clinics scheme",
        "acandabc copy.json",
        UserProfile(age=65),
        False,
    ),
    (
        "Delhi resident, age 35 -> eligible for Accidental Death Assistance (Delhi)",
        "adacw copy.json",
        UserProfile(age=35, state="Delhi"),
        True,
    ),
    (
        "Delhi resident, age 15 (below 18) -> NOT eligible for Accidental Death Assistance",
        "adacw copy.json",
        UserProfile(age=15, state="Delhi"),
        False,
    ),
    (
        "Puducherry resident, age 25 within 18-35 -> eligible for Advance High Skill Training",
        "ahst copy.json",
        UserProfile(age=25, state="Puducherry"),
        True,
    ),
    (
        "Puducherry resident, age 50 (above 35) -> NOT eligible for Advance High Skill Training",
        "ahst copy.json",
        UserProfile(age=50, state="Puducherry"),
        False,
    ),
    (
        "SC category, Karnataka, age 25 -> eligible for Airavata Scheme",
        "airavata copy.json",
        UserProfile(age=25, state="Karnataka", category="sc", income_annual=400_000),
        True,
    ),
    (
        "OBC category (not SC), Karnataka, age 25 -> NOT eligible for Airavata Scheme",
        "airavata copy.json",
        UserProfile(age=25, state="Karnataka", category="obc", income_annual=400_000),
        False,
    ),
    (
        "Woman, Tamil Nadu, income 2L -> eligible for Amma Two Wheeler Scheme",
        "atwsfww copy.json",
        UserProfile(age=30, state="Tamil Nadu", gender="female", income_annual=200_000),
        True,
    ),
    (
        "Male applicant -> NOT eligible for Amma Two Wheeler Scheme (women only)",
        "atwsfww copy.json",
        UserProfile(age=30, state="Tamil Nadu", gender="male", income_annual=200_000),
        False,
    ),
    (
        "Kerala resident, age 60, income 50k -> eligible for Abhayakiranam Scheme",
        "as-fadw copy.json",
        UserProfile(age=60, state="Kerala", income_annual=50_000),
        True,
    ),
    (
        "Kerala resident, age 40 (below 50 age-limit) -> NOT eligible for Abhayakiranam Scheme",
        "as-fadw copy.json",
        UserProfile(age=40, state="Kerala", income_annual=50_000),
        False,
    ),
    (
        "Puducherry, age 30, disabled -> eligible for Annual Tour to Differently Abled Persons",
        "atdap copy.json",
        UserProfile(age=30, state="Puducherry", disability=True, income_annual=50_000),
        True,
    ),
    (
        "Puducherry, age 30, NOT disabled -> NOT eligible for Annual Tour to Differently Abled Persons",
        "atdap copy.json",
        UserProfile(age=30, state="Puducherry", disability=False, income_annual=50_000),
        False,
    ),
    (
        "West Bengal resident, age 40 -> eligible for Bina Mulya Samajik Suraksha Yojana",
        "bmssy.json",
        UserProfile(age=40, state="West Bengal"),
        True,
    ),
    (
        "West Bengal resident, age 70 (above 60) -> NOT eligible for Bina Mulya Samajik Suraksha Yojana",
        "bmssy.json",
        UserProfile(age=70, state="West Bengal"),
        False,
    ),
    (
        "Low income minority applicant -> eligible for Alpasankhyak Post-Maitrik Chhaatravrtti Yojana",
        "apmcy copy.json",
        UserProfile(age=20, category="general", income_annual=100_000),
        True,
    ),
    (
        "High income (10L, well above 2L cap) -> NOT eligible for Alpasankhyak Post-Maitrik Chhaatravrtti Yojana",
        "apmcy copy.json",
        UserProfile(age=20, category="general", income_annual=1_000_000),
        False,
    ),
]


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    correct = 0
    unverifiable_count = 0
    rows = []

    for description, scheme_file, profile, expected in TEST_CASES:
        scheme = _load(scheme_file)
        result = check_eligibility(profile, scheme)
        actual = result["eligible"]
        match = actual == expected
        has_unverifiable = bool(result["unverifiable_conditions"])

        correct += int(match)
        unverifiable_count += int(has_unverifiable)

        rows.append(
            {
                "description": description,
                "scheme_file": scheme_file,
                "scheme_name": scheme.get("metadata", {}).get("scheme_name"),
                "expected_eligible": expected,
                "actual_eligible": actual,
                "match": match,
                "unverifiable_conditions": result["unverifiable_conditions"],
                "failed_conditions": result["failed_conditions"],
            }
        )

        status = "PASS" if match else "FAIL"
        flag = " [has unverifiable conditions]" if has_unverifiable else ""
        print(f"[{status}] {description}{flag}")
        if not match:
            print(f"         expected={expected} actual={actual} "
                  f"failed={result['failed_conditions']} unverifiable={result['unverifiable_conditions']}")

    total = len(TEST_CASES)
    accuracy = correct / total * 100 if total else 0.0
    unverifiable_pct = unverifiable_count / total * 100 if total else 0.0

    print("\n" + "=" * 70)
    print("ELIGIBILITY EVALUATION SUMMARY")
    print("=" * 70)
    print(f"  Total test cases: {total}")
    print(f"  Correct: {correct}")
    print(f"  Accuracy: {accuracy:.1f}%")
    print(f"  Cases with unverifiable conditions: {unverifiable_count} ({unverifiable_pct:.1f}%)")

    out_path = Path(__file__).resolve().parent / "eval_eligibility_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "accuracy_pct": round(accuracy, 1),
                "unverifiable_pct": round(unverifiable_pct, 1),
                "total": total,
                "correct": correct,
                "rows": rows,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    print(f"\nFull results written to {out_path}")

    return {"accuracy_pct": accuracy, "unverifiable_pct": unverifiable_pct}


if __name__ == "__main__":
    main()
