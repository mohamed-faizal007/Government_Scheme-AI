import os
import json
import time
import traceback
from pathlib import Path

from dotenv import load_dotenv
from google import genai

from extract_text import extract_text_from_pdf
from preprocess import preprocess_text
from postprocess import clean_json
from prompts import EXTRACTION_PROMPT
from schema import Scheme

# =====================================================
# Load API Key
# =====================================================

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("❌ GEMINI_API_KEY not found!")

client = genai.Client(api_key=API_KEY)

# =====================================================
# Paths
# =====================================================

PDF_FOLDER = Path("dataset/gov_myscheme/text_data")
OUTPUT_FOLDER = Path(OUTPUT_FOLDER = Path("dataset/gov_myscheme/json_output"))
LOG_FOLDER = Path("backend/logs")

OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
LOG_FOLDER.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_FOLDER / "extraction_errors.log"

# =====================================================
# PDF List
# =====================================================

pdf_files = sorted(PDF_FOLDER.glob("*.pdf"))

total = len(pdf_files)

print("=" * 70)
print(f"Found {total} PDF files")
print("=" * 70)

start_time = time.time()

success = 0
failed = 0
skipped = 0

# =====================================================
# Process PDFs
# =====================================================

for index, pdf_path in enumerate(pdf_files, start=1):

    output_file = OUTPUT_FOLDER / f"{pdf_path.stem}.json"

    # Skip existing files

    if output_file.exists():
        skipped += 1
        print(f"[{index}/{total}] ⏭ Skipped : {pdf_path.name}")
        continue

    print(f"\n[{index}/{total}] Processing : {pdf_path.name}")

    retries = 3

    while retries > 0:

        try:

            # -----------------------------------------
            # Extract Text
            # -----------------------------------------

            raw_text = extract_text_from_pdf(str(pdf_path))

            clean_text = preprocess_text(raw_text)

            # -----------------------------------------
            # Gemini Prompt
            # -----------------------------------------

            prompt = f"""
{EXTRACTION_PROMPT}

----------------------------

{clean_text}

----------------------------
"""

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": Scheme,
                    "temperature": 0.1,
                },
            )

            # -----------------------------------------
            # Validate
            # -----------------------------------------

            scheme = Scheme.model_validate_json(response.text)

            cleaned_json = clean_json(scheme.model_dump())

            # -----------------------------------------
            # Save
            # -----------------------------------------

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(
                    cleaned_json,
                    f,
                    indent=4,
                    ensure_ascii=False,
                )

            success += 1

            print("✅ Saved")

            break

        except Exception as e:

            retries -= 1

            if retries > 0:

                print("⚠ Retrying in 5 seconds...")

                time.sleep(5)

            else:

                failed += 1

                print("❌ Failed")

                with open(LOG_FILE, "a", encoding="utf-8") as log:

                    log.write("=" * 80 + "\n")
                    log.write(f"PDF : {pdf_path.name}\n")
                    log.write(str(e) + "\n")
                    log.write(traceback.format_exc())
                    log.write("\n\n")

elapsed = time.time() - start_time

# =====================================================
# Summary
# =====================================================

print("\n")
print("=" * 70)
print("EXTRACTION COMPLETED")
print("=" * 70)

print(f"Total PDFs      : {total}")
print(f"Successful      : {success}")
print(f"Skipped         : {skipped}")
print(f"Failed          : {failed}")
print(f"Elapsed Time    : {elapsed / 60:.2f} minutes")

print("=" * 70)

if failed > 0:
    print(f"Check log file: {LOG_FILE}")

print("=" * 70)