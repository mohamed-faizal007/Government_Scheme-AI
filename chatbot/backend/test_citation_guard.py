"""Citation-guard name matching checks (no LLM, no database).
Run: python -m chatbot.backend.test_citation_guard  (from repo root)
"""
from .rag.generator import names_scheme

CASES = [
    ("trailing hyphen in stored name", "Abhayakiranam Scheme-",
     "The Abhayakiranam Scheme provides Rs 1,000 per month to relatives of destitute widows.", True),
    ("answer glues a non-breaking hyphen after the name", "Abhayakiranam Scheme-",
     "The Abhayakiranam Scheme‑provides Rs 1,000 per month.", True),
    ("short stored name, answer does not name it", "Dr. B.",
     "This scheme gives financial help to eligible families in Kerala.", False),
    ("'Dr. B.' normalises to 5 characters, so an answer that literally names it does match", "Dr. B.",
     "Contact Dr. B. for details.", True),
    ("non-breaking hyphen in stored name", "Chief Minister‑Kanya Utthan Yojana",
     "The Chief Minister-Kanya Utthan Yojana offers a grant to girls.", True),
    ("non-breaking hyphen in the answer", "Mukhya Mantri-Seva Yojana",
     "Under the Mukhya Mantri‑Seva Yojana, workers receive aid.", True),
    ("unrelated answer", "Atal Pension Yojana", "The capital of France is Paris.", False),
    ("1-character stored name 'E.'", "E.", "The scheme e. provides help and e is a letter.", False),
    ("stored name that is only a quote", "'", "The 'scheme' pays Rs 500.", False),
    ("quoted name in the answer", "Assam Arogya Nidhi Scheme",
     "The “Assam Arogya Nidhi Scheme” helps patients.", True),
    ("repeated spaces and case", "Aam  Aadmi Bima   Yojana", "aam aadmi bima yojana (AABY) is an insurance scheme.", True),
]


def main() -> None:
    failures = 0
    for label, name, answer, expected in CASES:
        got = names_scheme(answer, name)
        ok = got == expected
        failures += not ok
        print(f"[{'PASS' if ok else 'FAIL'}] {label}: stored={name!r} -> match={got} (expected {expected})")
    print(f"\n{len(CASES) - failures}/{len(CASES)} passed")
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
