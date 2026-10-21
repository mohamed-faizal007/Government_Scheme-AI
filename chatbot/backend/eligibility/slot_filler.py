"""Decides which profile field to ask about next, in a fixed priority order.
Run test: python -m chatbot.backend.eligibility.slot_filler  (from repo root)
"""
from .user_profile import UserProfile

QUESTIONS = {
    "age": "Could you tell me your age?",
    "state": "Which state are you in?",
    "income_annual": "What's your approximate annual family income?",
    "category": "Which category do you belong to — general, OBC, SC, or ST?",
    "gender": "And just to check eligibility properly, what's your gender?",
}

PRIORITY = ["age", "state", "income_annual", "category", "gender"]


def get_next_slot(profile: UserProfile, skipped: set | None = None) -> str | None:
    """First priority field that is empty and not skipped by the user."""
    for field in PRIORITY:
        if getattr(profile, field) is None and field not in (skipped or ()):
            return field
    return None


def get_next_question(profile: UserProfile, skipped: set | None = None) -> str | None:
    slot = get_next_slot(profile, skipped)
    return QUESTIONS[slot] if slot else None


if __name__ == "__main__":
    profile = UserProfile()
    print(get_next_question(profile))

    profile = UserProfile(age=30, state="Tamil Nadu")
    print(get_next_question(profile))

    profile = UserProfile(age=30, state="Tamil Nadu", income_annual=120000, category="sc", gender="male")
    print(get_next_question(profile))
