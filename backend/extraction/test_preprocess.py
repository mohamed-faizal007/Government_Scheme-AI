from preprocess import preprocess_text

# ==========================================================
# REGRESSION TEST
# ==========================================================
# Proves the word-boundary fix in preprocess.py:
#   - real words that merely CONTAIN a noise fragment ("Eng") survive
#   - genuine UI/webpage noise phrases are still stripped
#   - section headings survive and still get paragraph breaks
# ==========================================================

CASES = [
    # (description, input, must_contain, must_not_contain)
    (
        "'Engineer' must survive whole (old bug turned it into 'ineer')",
        "Plan certified by the Assistant Engineer (Civil).",
        ["Assistant Engineer (Civil)"],
        [],
    ),
    (
        "'England' must survive whole (old bug turned it into 'land')",
        "Applicants from England are eligible.",
        ["from England are eligible"],
        [],
    ),
    (
        "'Sign In' noise must still be stripped",
        "Please Sign In before applying.",
        [],
        ["Sign In"],
    ),
    (
        "'Apply Now' noise must still be stripped",
        "Click Apply Now to submit your form.",
        [],
        ["Apply Now"],
    ),
    (
        "'Was this helpful?' noise must still be stripped",
        "Thank you for reading. Was this helpful? Share your feedback.",
        [],
        ["Was this helpful?"],
    ),
    (
        "'Benefits' heading must survive and gain a paragraph break",
        "Introduction: some text. Benefits Financial assistance of Rs 5000.",
        ["\n\nBenefits\n"],
        [],
    ),
    (
        "Glued 'ApplicationProcess' (no space) must still be split into a heading break",
        "some text.ApplicationProcessStep 1: submit the form.",
        ["\n\nApplication Process\n"],
        [],
    ),
]

failures = []

for description, sample, must_contain, must_not_contain in CASES:
    cleaned = preprocess_text(sample)
    case_errors = []

    for token in must_contain:
        if token not in cleaned:
            case_errors.append(f"expected {token!r} in output, got: {cleaned!r}")

    for token in must_not_contain:
        if token in cleaned:
            case_errors.append(f"did not expect {token!r} in output, got: {cleaned!r}")

    print(f"{'FAIL' if case_errors else 'PASS'}  {description}")
    print(f"      input : {sample!r}")
    print(f"      output: {cleaned!r}\n")

    failures.extend(f"[{description}] {err}" for err in case_errors)

print("=" * 80)
if failures:
    print(f"{len(failures)} FAILURE(S)")
    for f in failures:
        print(" -", f)
    raise SystemExit(1)
else:
    print("ALL CHECKS PASSED")
