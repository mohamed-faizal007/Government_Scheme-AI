"""
PDF -> JSON pipeline using ONLY:
  1. Hosted Unstructured API (parsing into structured elements/raw text)
  2. Deterministic boundary recovery (heading-vocabulary + word-boundary
     regex passes -- see insert_boundaries.py) -- needed because this
     dataset's PDFs are webpage-to-PDF renders with no visual heading
     formatting, so Unstructured's own Title detection finds nothing to
     classify (confirmed 0/15 sampled PDFs across both "fast" and
     "hi_res" strategies)
  3. Local sentence-embedding similarity (heading -> schema category)
  4. Rule-based verbatim extraction (heading content -> JSON field)

No generative LLM anywhere in this pipeline. Deterministic: parsing +
boundary recovery + classification + verbatim extraction only.

This is a Step 3 TEST RUN on exactly 5 PDFs, writing to a separate test
folder. It does not touch dataset/gov_myscheme/json_output/ and does not
process the rest of the dataset.
"""

import json
import sys
from pathlib import Path

# Windows console defaults to cp1252, which can't encode characters this
# dataset contains verbatim (e.g. the rupee sign). Reports go to stdout,
# not through the UTF-8 file writes below, so this must be set explicitly.
sys.stdout.reconfigure(encoding="utf-8")

from classify_headings import apply_gap_chain_suppression, classify_headings
from extract_sections import (
    collect_sections_by_category,
    content_items,
    extract_faq_pairs,
    filter_label_artifacts,
    split_into_sections,
)
from insert_boundaries import insert_boundaries, strip_footer_noise
from parse_unstructured import partition_pdf, pages_consumed
from postprocess import clean_json
from preprocess import REMOVE_PHRASES, _replace_whole_phrase
from schema import Scheme
from validate_json import validate_scheme_dict

# ==========================================================
# CONFIGURATION
# ==========================================================

PDF_FOLDER = Path("dataset/gov_myscheme/unique_pdfs")
OUTPUT_FOLDER = Path("dataset/gov_myscheme/test_output_unstructured")
NUM_TEST_PDFS = 5
SNIPPET_LEN = 500

OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

# Categories that pull straight from a single classified heading into a
# single list field of Scheme.
LIST_FIELD_CATEGORIES = {
    "objectives": ("overview", "objectives"),
    "benefits": ("benefits", "other_benefits"),
    "eligibility": ("eligibility", "conditions"),
    "exclusions": ("eligibility", "exclusions"),
    "documents_required": ("application", "documents"),
    "application_process": ("application", "steps"),
}


def strip_noise(text: str) -> str:
    """
    Remove known website-chrome phrases (Sign In, Cancel, Apply Now, ...).
    Reuses preprocess.py's REMOVE_PHRASES / matching logic rather than
    duplicating it. Must run AFTER boundary insertion, so noise removal
    operates on text that already has real section/word boundaries.
    """

    for phrase in REMOVE_PHRASES:
        text = _replace_whole_phrase(text, phrase, "")
    return text


# Button/CTA labels that contain heading-vocabulary words (e.g. "Check
# Eligibility" contains "Eligibility") and so can fire a false heading
# match if left in place until after boundary insertion. Stripped BEFORE
# insert_boundaries() specifically for this reason -- unlike the rest of
# REMOVE_PHRASES, which runs after boundary insertion by design (see
# strip_noise above) since it doesn't share this problem.
_BUTTON_PHRASES = ["Check Eligibility", "Apply Now"]


def strip_button_phrases(text: str) -> str:
    """Remove known button/CTA label text before heading-vocabulary
    matching runs, so it can't open a false section boundary."""

    for phrase in _BUTTON_PHRASES:
        text = _replace_whole_phrase(text, phrase, "")
    return text


# ==========================================================
# PER-PDF PIPELINE
# ==========================================================

def build_scheme_dict(by_category: dict, scheme_name: str, description: str = "") -> dict:
    data = {
        "metadata": {"scheme_name": scheme_name},
        "overview": {"description": description, "objectives": []},
        "benefits": {"other_benefits": []},
        "eligibility": {"conditions": [], "exclusions": []},
        "application": {"documents": [], "steps": []},
        "faq": [],
    }

    for category, (section, field) in LIST_FIELD_CATEGORIES.items():
        data[section][field] = filter_label_artifacts(
            by_category.get(category, []), scheme_name
        )

    data["faq"] = [
        {"question": q["question"], "answer": q["answer"]}
        for q in extract_faq_pairs(by_category.get("faqs", []))
    ]

    return data


def process_pdf(pdf_path: Path) -> dict:
    elements = partition_pdf(str(pdf_path))
    pages = pages_consumed(elements)

    raw_text = "\n".join((el.get("text") or "") for el in elements)

    footer_stripped_text = strip_footer_noise(raw_text)
    button_stripped_text = strip_button_phrases(footer_stripped_text)
    boundary_text = insert_boundaries(button_stripped_text)
    clean_text = strip_noise(boundary_text)

    preamble, sections = split_into_sections(clean_text)
    heading_texts = [heading for heading, _ in sections]

    classifications = classify_headings(heading_texts)
    classifications = apply_gap_chain_suppression(sections, classifications)

    preamble_items = content_items(preamble)
    scheme_name = preamble_items[0] if preamble_items else pdf_path.stem

    # First orphan block found (nav-bar chain's trailing real content) is
    # captured verbatim into overview.description, unclassified. Second
    # occurrence (this dataset's PDFs render the whole page twice) is
    # skipped -- first occurrence only.
    description = ""
    for (_, content_text), classification in zip(sections, classifications):
        if classification.get("orphan") and not description:
            description = content_text.strip()
            break

    by_category = collect_sections_by_category(sections, classifications)

    scheme_dict = build_scheme_dict(by_category, scheme_name, description)
    scheme_dict = clean_json(scheme_dict)

    scheme = Scheme.model_validate(scheme_dict)
    final_json = scheme.model_dump()

    validation = validate_scheme_dict(final_json)

    return {
        "pdf": pdf_path.name,
        "pages_consumed": pages,
        "element_count": len(elements),
        "raw_text": raw_text,
        "boundary_text": boundary_text,
        "scheme_name": scheme_name,
        "classifications": classifications,
        "final_json": final_json,
        "valid": validation.is_valid,
        "validation_errors": validation.errors,
    }


# ==========================================================
# REPORTING
# ==========================================================

def print_report(result: dict) -> None:
    print("\n" + "=" * 80)
    print(f"PDF: {result['pdf']}")
    print("=" * 80)

    print(f"Elements parsed (Unstructured) : {result['element_count']}")
    print(f"Pages consumed                 : {result['pages_consumed']}")
    print(f"Schema valid                   : {result['valid']}")

    if not result["valid"]:
        for err in result["validation_errors"]:
            print(f"    INVALID -> {err.field}: {err.message}")

    print("\n--- RAW TEXT (before boundary insertion), first "
          f"{SNIPPET_LEN} chars ---")
    print(result["raw_text"][:SNIPPET_LEN])

    print("\n--- AFTER boundary insertion, first "
          f"{SNIPPET_LEN} chars ---")
    print(result["boundary_text"][:SNIPPET_LEN])

    print(f"\nDetected scheme_name (preamble, first item): {result['scheme_name']!r}")

    print("\nHeadings detected & classification:")

    if not result["classifications"]:
        print("  (no heading-vocabulary matches found)")

    low_confidence = []

    for c in result["classifications"]:
        flag = "" if c["confident"] else "  <-- LOW CONFIDENCE"
        heading_display = c["heading"].replace("\n", " ")
        print(f"  [{heading_display}] -> {c['category']} (score={c['score']:.3f}){flag}")

        if not c["confident"]:
            low_confidence.append(c)

    if low_confidence:
        print("\nFlagged (score < 0.5, not used in JSON):")
        for c in low_confidence:
            heading_display = c["heading"].replace("\n", " ")
            print(f"  - \"{heading_display}\" best guess={c['category']} score={c['score']:.3f}")

    print("\nFinal JSON:")
    print(json.dumps(result["final_json"], indent=2, ensure_ascii=False))


# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":
    all_pdfs = sorted(PDF_FOLDER.glob("*.pdf"))
    test_pdfs = all_pdfs[:NUM_TEST_PDFS]

    print(f"Running test pipeline on {len(test_pdfs)} PDFs")
    print(f"Output folder: {OUTPUT_FOLDER.resolve()}")

    total_pages = 0
    results = []

    for pdf_path in test_pdfs:
        try:
            result = process_pdf(pdf_path)
        except Exception as exc:
            print(f"\nFAILED: {pdf_path.name} -> {exc}")
            raise

        results.append(result)
        total_pages += result["pages_consumed"]

        print_report(result)

        if result["valid"]:
            output_file = OUTPUT_FOLDER / f"{pdf_path.stem}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result["final_json"], f, indent=4, ensure_ascii=False)
        else:
            print(f"NOT SAVED (schema validation failed): {pdf_path.name}")

    print("\n" + "=" * 80)
    print("TEST RUN SUMMARY")
    print("=" * 80)
    print(f"PDFs processed        : {len(results)}")
    print(f"Total pages consumed  : {total_pages}")
    print(f"Output folder         : {OUTPUT_FOLDER.resolve()}")
    print("Stopping here for review -- json_output/ was not touched, no further PDFs processed.")
