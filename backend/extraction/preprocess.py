import re


REMOVE_PHRASES = [
    "Are you sure you want to sign out?",
    "Cancel",
    "Sign Out",
    "Sign In",
    "Feedback",
    "Something went wrong.",
    "Please try again later.",
    "Apply Now",
    "Check Eligibility",
    "Back",
    "Details",
    "Benefits",
    "Eligibility",
    "Exclusions",
    "Application Process",
    "Documents Required",
    "Frequently Asked Questions",
    "Sources And References",
    "Eng",
    "English",
]


def preprocess_text(text: str) -> str:
    """
    Clean noisy text extracted from MyScheme PDFs.
    """

    if not text:
        return ""

    # -------------------------------
    # Normalize whitespace
    # -------------------------------

    text = text.replace("\r", "\n")
    text = re.sub(r"\s+", " ", text)

    # -------------------------------
    # Remove common UI phrases
    # -------------------------------

    for phrase in REMOVE_PHRASES:
        text = text.replace(phrase, "")

    # -------------------------------
    # Remove repeated spaces
    # -------------------------------

    text = re.sub(r" {2,}", " ", text)

    # -------------------------------
    # Try to separate headings
    # -------------------------------

    headings = [
        "Introduction:",
        "Benefits",
        "Eligibility",
        "Exclusions",
        "Application Process",
        "Documents Required",
        "Frequently Asked Questions",
    ]

    for heading in headings:
        text = text.replace(heading, f"\n\n{heading}\n")

    return text.strip()