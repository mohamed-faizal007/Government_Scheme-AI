from functools import lru_cache
from typing import Dict, List, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer

# ==========================================================
# CONFIG
# ==========================================================

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Below this cosine similarity, a heading is not confidently assigned to
# any category -- flag it instead of forcing a guess.
CONFIDENCE_THRESHOLD = 0.5

# Per-category overrides, applied only when that category is the best
# match. Not a global threshold change: after the seed-phrase fix above,
# "benefits" (bare "Benefits" heading) and "objectives" (bare
# "Introduction" heading) still consistently score 0.476-0.483 on their
# correct match across every test PDF -- a stable few points under 0.5,
# not noise. "exclusions" needed no override; its seed fix alone pushed
# it to 0.505. The other 4 categories are untouched (still 0.5) since
# they were never observed scoring near the boundary.
CATEGORY_THRESHOLD_OVERRIDES: Dict[str, float] = {
    "benefits": 0.45,
    "objectives": 0.45,
}

# Canonical schema categories. Several seed phrases per category are
# embedded and averaged, so the classifier isn't relying on a single
# wording -- this is still pure embedding similarity, no LLM involved.
#
# Every category also carries at least one bare-word/short-heading seed
# (e.g. "Benefits", not just "Benefits of the scheme") -- the 5-PDF test
# run showed short, heading-style seeds score real headings noticeably
# higher than full descriptive sentences do (eligibility/documents_required
# both used short seeds and passed comfortably; objectives/benefits/
# exclusions used only sentence-length seeds and their real headings
# scored 0.32-0.47, just under the 0.5 threshold, despite already being
# the best-matching category every time). The bare-word additions below
# are pulled from the heading vocabulary already validated in
# preprocess.py's HEADINGS and insert_boundaries.py's
# EXTRA_HEADING_SYNONYMS, not invented fresh, plus the literal near-miss
# heading text observed in that test ("Financial Assistance", "Introduction").
CATEGORY_SEED_PHRASES: Dict[str, List[str]] = {
    "objectives": [
        "Objectives",
        "Introduction",
        "Objectives of the scheme",
        "Purpose and goals of the scheme",
        "About the scheme",
    ],
    "benefits": [
        "Benefits",
        "Financial Assistance",
        "Support Available",
        "Benefits of the scheme",
        "Financial assistance provided",
        "What you get from the scheme",
    ],
    "eligibility": [
        "Eligibility",
        "Eligibility criteria",
        "Who can apply for the scheme",
        "Conditions to qualify",
    ],
    "exclusions": [
        "Exclusions",
        "Not Eligible",
        "Exclusions from the scheme",
        "Who is not eligible",
        "Ineligibility conditions",
    ],
    "documents_required": [
        "Documents Required",
        "Documents required for application",
        "List of documents needed",
        "Required documentation",
    ],
    "application_process": [
        "Application Process",
        "How to Apply",
        "Application process",
        "How to apply for the scheme",
        "Steps to apply",
    ],
    "faqs": [
        "Frequently Asked Questions",
        "FAQs",
        "Frequently asked questions",
        "Questions and answers about the scheme",
        "FAQ",
    ],
}


# ==========================================================
# MODEL / EMBEDDINGS (computed once, reused for every PDF)
# ==========================================================

@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


@lru_cache(maxsize=1)
def _get_category_embeddings() -> Dict[str, np.ndarray]:
    model = _get_model()

    embeddings = {}

    for category, phrases in CATEGORY_SEED_PHRASES.items():
        vectors = model.encode(phrases, normalize_embeddings=True)
        embeddings[category] = np.mean(vectors, axis=0)

    return embeddings


# ==========================================================
# CLASSIFICATION
# ==========================================================

def classify_heading(heading_text: str) -> Tuple[str, float]:
    """
    Embed one heading and return (best_matching_category, cosine_similarity).
    """

    model = _get_model()
    category_embeddings = _get_category_embeddings()

    heading_vector = model.encode([heading_text], normalize_embeddings=True)[0]

    best_category = None
    best_score = -1.0

    for category, category_vector in category_embeddings.items():
        score = float(np.dot(heading_vector, category_vector))

        if score > best_score:
            best_score = score
            best_category = category

    return best_category, best_score


def _merge_duplicate_heading_continuations(results: List[Dict]) -> List[Dict]:
    """
    A heading-vocabulary term (e.g. "Objective") can fire a second time
    mid-paragraph, inside content that is really a continuation of the
    section that same heading text already opened -- not a new section.
    Classifying that second occurrence independently risks a different
    (wrong) category, which truncates the real section and leaks its
    remainder into whatever category the duplicate happened to score
    highest on.

    Detect this by exact (case/whitespace-insensitive) heading-text repeat
    against the immediately preceding heading, and force the repeat to
    inherit the preceding heading's category/confidence -- a continuation
    marker, not a new section boundary. `collect_sections_by_category`
    already concatenates same-category content in document order, so this
    is enough to merge the split content back into one section.
    """

    merged: List[Dict] = []

    for result in results:
        if merged and result["heading"].strip().lower() == merged[-1]["heading"].strip().lower():
            previous = merged[-1]
            merged.append({
                "heading": result["heading"],
                "category": previous["category"],
                "score": previous["score"],
                "confident": previous["confident"],
                "continuation": True,
            })
        else:
            merged.append({**result, "continuation": False})

    return merged


def classify_headings(headings: List[str]) -> List[Dict]:
    """
    Classify a batch of heading strings.

    Returns one dict per heading:
      {"heading": str, "category": str, "score": float, "confident": bool,
       "continuation": bool}
    """

    results = []

    for heading in headings:
        category, score = classify_heading(heading)
        threshold = CATEGORY_THRESHOLD_OVERRIDES.get(category, CONFIDENCE_THRESHOLD)

        results.append({
            "heading": heading,
            "category": category,
            "score": score,
            "confident": score >= threshold,
        })

    return _merge_duplicate_heading_continuations(results)


def apply_gap_chain_suppression(sections: List[Tuple[str, str]], classifications: List[Dict]) -> List[Dict]:
    """
    Detect nav-bar/tab-list chrome: a run of consecutive heading-vocabulary
    matches connected by exactly zero characters of content between them
    (e.g. "...DetailsBenefitsEligibilityApplication ProcessDocuments
    RequiredFrequently Asked QuestionsSources And References..." -- webpage
    tab labels glued together with no real content). Verified safe across
    an 11-file sweep: real section content never has zero characters
    before the next heading match, so a chain of length >= 2 is always
    chrome, never a false positive.

    A chain is a maximal run of sections[i] where content_text == "" for
    every member except possibly the last. The last member's own content
    is NOT empty -- it's the real content that immediately follows the
    chrome (e.g. leftover popup noise + the scheme's own description/
    objective paragraph, ending right before the next real heading) --
    but it must not be embedding-classified either, since the heading
    text that opened it ("Sources And References", in this dataset) is
    itself still just chrome, and scoring it normally either misplaces
    this content or drops it silently (observed: scores low-confidence
    against every category, so collect_sections_by_category would drop
    it entirely). Flagged "orphan" instead, for verbatim capture into
    overview.description by the caller.

    Every classification dict gains "suppressed" (bool) and "orphan"
    (bool) keys; both default to False when no chain is detected.
    """

    results = [dict(c) for c in classifications]
    for r in results:
        r.setdefault("suppressed", False)
        r.setdefault("orphan", False)

    n = len(sections)
    i = 0
    while i < n:
        chain_start = i
        while i < n - 1 and sections[i][1] == "":
            i += 1
        chain_end = i
        chain_length = chain_end - chain_start + 1

        if chain_length >= 2:
            for j in range(chain_start, chain_end):
                results[j]["suppressed"] = True
            results[chain_end]["suppressed"] = True
            results[chain_end]["orphan"] = True

        i += 1

    return results


if __name__ == "__main__":
    sample_headings = [
        "Benefits",
        "Eligibility",
        "Documents Required",
        "Application Process",
        "Frequently Asked Questions",
        "Exclusions",
        "Objectives",
        "Contact Us",
    ]

    for result in classify_headings(sample_headings):
        print(
            f"{result['heading']:30s} -> {result['category']:20s} "
            f"score={result['score']:.3f} confident={result['confident']}"
        )
