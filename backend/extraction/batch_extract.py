import json
import os
import time
import traceback
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from google import genai

from extract_text import extract_text_from_pdf
from preprocess import preprocess_text
from postprocess import clean_json
from prompts import EXTRACTION_PROMPT
from schema import Scheme

# ==========================================================
# CONFIGURATION
# ==========================================================

PDF_FOLDER = Path("dataset/gov_myscheme/unique_pdfs")
OUTPUT_FOLDER = Path("dataset/gov_myscheme/json_output")
LOG_FOLDER = Path("dataset/gov_myscheme/logs")

OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
LOG_FOLDER.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_FOLDER / "extraction_errors.log"

REQUEST_DELAY = 2
MAX_RETRIES = 5

# ==========================================================
# GEMINI
# ==========================================================

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env")

client = genai.Client(api_key=API_KEY)

# ==========================================================
# FIND UNPROCESSED PDFs
# ==========================================================

all_pdfs = sorted(PDF_FOLDER.glob("*.pdf"))

remaining_pdfs = []

for pdf in all_pdfs:

    output_json = OUTPUT_FOLDER / f"{pdf.stem}.json"

    if not output_json.exists():
        remaining_pdfs.append(pdf)

print("\n" + "=" * 80)
print(f"Total PDFs           : {len(all_pdfs)}")
print(f"Already Processed    : {len(all_pdfs)-len(remaining_pdfs)}")
print(f"Remaining PDFs       : {len(remaining_pdfs)}")
print("=" * 80)

if len(remaining_pdfs) == 0:
    print("\nEverything has already been processed.")
    exit()

# ==========================================================
# ASK USER
# ==========================================================

while True:

    try:

        batch_size = int(
            input("\nHow many PDFs do you want to process this run? : ")
        )

        if batch_size <= 0:
            print("Please enter a positive number.")
            continue

        break

    except ValueError:
        print("Enter a valid integer.")

pdf_files = remaining_pdfs[:batch_size]

TOTAL = len(pdf_files)

print("\n" + "=" * 80)
print("Batch Summary")
print("=" * 80)
print(f"Processing this run : {TOTAL}")
print("=" * 80)

success = 0
failed = 0

start_time = time.time()

# ==========================================================
# PROCESS
# ==========================================================

for idx, pdf_path in enumerate(pdf_files, start=1):

    print("\n" + "-" * 80)
    print(f"[{idx}/{TOTAL}] {pdf_path.name}")

    output_file = OUTPUT_FOLDER / f"{pdf_path.stem}.json"

    retry = 0

    while retry < MAX_RETRIES:

        try:

            # --------------------------------------------------

            raw_text = extract_text_from_pdf(str(pdf_path))

            clean_text = preprocess_text(raw_text)

            prompt = f"""
{EXTRACTION_PROMPT}

------------------------

{clean_text}

------------------------
"""

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={
                    "temperature": 0.1,
                    "response_mime_type": "application/json",
                    "response_schema": Scheme,
                },
            )

            scheme = Scheme.model_validate_json(response.text)

            final_json = clean_json(
                scheme.model_dump()
            )

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(
                    final_json,
                    f,
                    indent=4,
                    ensure_ascii=False,
                )

            success += 1

            elapsed = time.time() - start_time

            average = elapsed / max(success + failed, 1)

            remaining = TOTAL - idx

            eta = timedelta(seconds=int(average * remaining))

            print("SUCCESS")
            print(f"Elapsed : {timedelta(seconds=int(elapsed))}")
            print(f"ETA      : {eta}")

            time.sleep(REQUEST_DELAY)

            break

        except KeyboardInterrupt:

            print("\nExtraction stopped by user.")
            print("Run the script again to resume automatically.")
            exit()

        except Exception as e:

            error_message = str(e).lower()

            quota_keywords = [
                "429",
                "resource_exhausted",
                "quota",
                "rate limit",
                "too many requests",
                "resource exhausted",
                "quota exceeded",
            ]

            # --------------------------------------------------
            # DAILY QUOTA / RATE LIMIT
            # --------------------------------------------------

            if any(keyword in error_message for keyword in quota_keywords):

                print("\n" + "=" * 80)
                print("🚨 GEMINI FREE API QUOTA REACHED")
                print("=" * 80)
                print("The free Gemini API quota has been exhausted.")
                print("All completed JSON files have already been saved.")
                print("No work has been lost.")
                print("\nYou can simply run this script again later (or tomorrow).")
                print("It will automatically continue from where it stopped.")
                print("=" * 80)

                with open(LOG_FILE, "a", encoding="utf-8") as log:

                    log.write("=" * 80 + "\n")
                    log.write("GEMINI QUOTA REACHED\n")
                    log.write(f"Stopped at PDF : {pdf_path.name}\n")
                    log.write(str(e) + "\n\n")

                exit()

            # --------------------------------------------------
            # NORMAL RETRY
            # --------------------------------------------------

            retry += 1

            if retry < MAX_RETRIES:

                wait = min(10 * (2 ** (retry - 1)), 300)

                print(f"\nRetry {retry}/{MAX_RETRIES}")
                print(f"Reason : {e}")
                print(f"Waiting {wait} seconds...\n")

                time.sleep(wait)

            else:

                failed += 1

                print("\nFAILED")
                print(e)

                with open(LOG_FILE, "a", encoding="utf-8") as log:

                    log.write("=" * 80 + "\n")
                    log.write(f"PDF : {pdf_path.name}\n")
                    log.write(str(e) + "\n\n")
                    log.write(traceback.format_exc())
                    log.write("\n\n")

# ==========================================================
# SUMMARY
# ==========================================================

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

remaining = len([
    pdf
    for pdf in all_pdfs
    if not (OUTPUT_FOLDER / f"{pdf.stem}.json").exists()
])

print(f"\nRemaining PDFs : {remaining}")

if remaining == 0:
    print("\n🎉 Dataset extraction completed successfully!")

print("=" * 80)