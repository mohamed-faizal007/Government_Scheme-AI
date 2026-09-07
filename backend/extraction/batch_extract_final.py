import json
import os
import re
import sys
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from docling.document_converter import DocumentConverter
from openai import OpenAI

from preprocess import preprocess_text
from postprocess import clean_json
from schema import Scheme
from validate_json import validate_scheme_dict, validate_json_file

# ==========================================================
# CONFIGURATION
# ==========================================================
# Selected approach (see WORK_REPORT.md comparison): Docling -> Groq
# (openai/gpt-oss-120b), chosen for speed (~19s/PDF avg vs Qwen's
# ~185s/PDF) and for consistently following the JSON-only instruction.
#
# This is a SEPARATE file from batch_extract.py (PROJECT_PLAN.md Rule 1 /
# section 36 Step 5) -- the existing Gemini pipeline is untouched.

PDF_FOLDER = Path("dataset/gov_myscheme/unique_pdfs")
OUTPUT_FOLDER = Path("dataset/gov_myscheme/json_output")
LOG_FOLDER = Path("dataset/gov_myscheme/logs")

OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
LOG_FOLDER.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_FOLDER / "extraction_errors_groq.log"

MODEL = "openai/gpt-oss-120b"
MAX_RETRIES = 8
REQUEST_DELAY = 1

# Groq's free tier enforces a short, per-minute token throttle (observed:
# "Rate limit reached ... on tokens per minute (TPM) ... Please try again
# in 2.9s") -- this resolves within seconds and should just be retried,
# NOT treated as a hard stop like Gemini's daily quota in batch_extract.py.
# Only a genuinely long-lived daily/monthly exhaustion should abort the
# whole run, since retrying that would just waste hours.
HARD_STOP_KEYWORDS = [
    "requests per day",
    "tokens per day",
    "daily limit",
    "monthly limit",
]

EXTRACTION_PROMPT = """
You are an expert AI that extracts structured information from Indian
Government Scheme documents.

The document text below was parsed from a webpage-exported PDF and may
contain:
- navigation menus, buttons, and website chrome (Sign In, Cancel, Apply
  Now, Check Eligibility, Was this helpful?, ...)
- duplicated paragraphs
- encoding artifacts
- page numbers and footer boilerplate

Ignore all irrelevant webpage/navigation text. Extract only the actual
government scheme information.

Do not invent information. If a field is not mentioned in the document,
leave it as an empty string or empty list -- never guess or assume.

Preserve exact numbers, percentages, amounts, dates, and age/income
limits exactly as written in the source document.

If the document uses different section headings than the schema
(e.g. "Financial Assistance" instead of "Benefits", "Who Can Apply"
instead of "Eligibility"), map them to the closest matching field by
meaning, not by exact wording.
"""

# ==========================================================
# GROQ CLIENT
# ==========================================================

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env")

client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=API_KEY)

# Enforced structured output -- the model's response is constrained to
# this exact shape by Groq's API (same role Gemini's response_schema
# plays in batch_extract.py), so output validates against schema.py by
# construction rather than by hoping the model follows a prompt example.
SCHEME_JSON_SCHEMA = Scheme.model_json_schema()

# ==========================================================
# DOCLING (reused across PDFs -- expensive to initialize per-call)
# ==========================================================

converter = DocumentConverter()


def docling_to_text(pdf_path: Path) -> str:
    result = converter.convert(str(pdf_path))
    return result.document.export_to_markdown()


# ==========================================================
# CORE EXTRACTION
# ==========================================================

def extract_one(pdf_path: Path) -> Scheme:
    raw_text = docling_to_text(pdf_path)
    clean_text = preprocess_text(raw_text)

    prompt = f"""
{EXTRACTION_PROMPT}

------------------------

{clean_text}

------------------------
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "Scheme", "schema": SCHEME_JSON_SCHEMA},
        },
        temperature=0.1,
    )

    data = json.loads(response.choices[0].message.content)
    result = validate_scheme_dict(data)

    if not result.is_valid:
        details = "; ".join(f"{e.field}: {e.message}" for e in result.errors)
        raise ValueError(f"Schema validation failed: {details}")

    return result.scheme


def log_failure(pdf_path: Path, error: Exception) -> None:
    with open(LOG_FILE, "a", encoding="utf-8") as log:
        log.write("=" * 80 + "\n")
        log.write(f"Timestamp : {datetime.now().isoformat()}\n")
        log.write(f"PDF       : {pdf_path.name}\n")
        log.write(f"Error     : {error}\n")
        log.write(traceback.format_exc())
        log.write("\n\n")


def output_path_for(pdf_path: Path) -> Path:
    return OUTPUT_FOLDER / f"{pdf_path.stem}.json"


def has_valid_output(pdf_path: Path) -> bool:
    """
    Resume logic: skip a PDF only if it already has output that passes
    schema validation -- an existing-but-invalid file (e.g. left over
    from an interrupted run) is treated as not done and retried.
    """

    output_file = output_path_for(pdf_path)
    if not output_file.exists():
        return False
    return validate_json_file(output_file).is_valid


# ==========================================================
# MAIN
# ==========================================================

def main():
    all_pdfs = sorted(PDF_FOLDER.glob("*.pdf"))
    remaining_pdfs = [p for p in all_pdfs if not has_valid_output(p)]

    print("=" * 80)
    print(f"Total PDFs        : {len(all_pdfs)}")
    print(f"Already valid     : {len(all_pdfs) - len(remaining_pdfs)}")
    print(f"Remaining PDFs    : {len(remaining_pdfs)}")
    print("=" * 80)

    if not remaining_pdfs:
        print("\nEverything already has valid output.")
        return

    if len(sys.argv) > 1:
        batch_size = int(sys.argv[1])
    else:
        while True:
            try:
                batch_size = int(input("\nHow many PDFs do you want to process this run? : "))
                if batch_size > 0:
                    break
                print("Please enter a positive number.")
            except ValueError:
                print("Enter a valid integer.")

    pdf_files = remaining_pdfs[:batch_size]
    total = len(pdf_files)

    print("\n" + "=" * 80)
    print("Batch Summary")
    print("=" * 80)
    print(f"Processing this run : {total}")
    print("=" * 80)

    success = 0
    failed = 0
    start_time = time.time()

    for idx, pdf_path in enumerate(pdf_files, start=1):

        print("\n" + "-" * 80)
        print(f"[{idx}/{total}] {pdf_path.name}")

        retry = 0

        while retry < MAX_RETRIES:

            try:
                scheme = extract_one(pdf_path)
                final_json = clean_json(scheme.model_dump())

                output_file = output_path_for(pdf_path)
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(final_json, f, indent=4, ensure_ascii=False)

                success += 1

                elapsed = time.time() - start_time
                average = elapsed / max(success + failed, 1)
                eta = timedelta(seconds=int(average * (total - idx)))

                print("SUCCESS")
                print(f"Elapsed : {timedelta(seconds=int(elapsed))}")
                print(f"ETA     : {eta}")

                time.sleep(REQUEST_DELAY)
                break

            except KeyboardInterrupt:
                print("\nExtraction stopped by user.")
                print("Run the script again to resume automatically.")
                sys.exit(0)

            except Exception as e:

                error_message = str(e).lower()

                if any(keyword in error_message for keyword in HARD_STOP_KEYWORDS):
                    print("\n" + "=" * 80)
                    print("DAILY/MONTHLY QUOTA REACHED")
                    print("=" * 80)
                    print("All completed JSON files have already been saved.")
                    print("Run this script again later to resume from where it stopped.")
                    log_failure(pdf_path, e)
                    sys.exit(1)

                retry += 1

                if retry < MAX_RETRIES:
                    # Groq's per-minute token throttle tells us exactly
                    # how long to wait (e.g. "Please try again in 2.9s")
                    # -- use that directly when present, since it
                    # resolves far faster than the generic exponential
                    # backoff below.
                    retry_hint = re.search(r"try again in ([\d.]+)s", error_message)
                    wait = float(retry_hint.group(1)) + 1 if retry_hint else min(10 * (2 ** (retry - 1)), 300)
                else:
                    wait = None

                if wait is not None:
                    print(f"\nRetry {retry}/{MAX_RETRIES}")
                    print(f"Reason : {e}")
                    print(f"Waiting {wait:.1f} seconds...\n")
                    time.sleep(wait)
                else:
                    failed += 1
                    print("\nFAILED")
                    print(e)
                    log_failure(pdf_path, e)

    elapsed = timedelta(seconds=int(time.time() - start_time))

    print("\n")
    print("=" * 80)
    print("RUN COMPLETE")
    print("=" * 80)
    print(f"Successful : {success}")
    print(f"Failed     : {failed}")
    print(f"Elapsed    : {elapsed}")
    print("\nJSON Output")
    print(OUTPUT_FOLDER)
    print("\nError Log")
    print(LOG_FILE)

    remaining = len([p for p in all_pdfs if not has_valid_output(p)])
    print(f"\nRemaining PDFs : {remaining}")

    if remaining == 0:
        print("\nDataset extraction completed successfully!")

    print("=" * 80)


if __name__ == "__main__":
    main()
