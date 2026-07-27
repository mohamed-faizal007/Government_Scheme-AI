'''import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai

from extract_text import extract_text_from_pdf
from prompts import EXTRACTION_PROMPT

# -------------------------------
# Load Environment Variables
# -------------------------------

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env")

client = genai.Client(api_key=API_KEY)

# -------------------------------
# Select PDF
# -------------------------------

PDF_PATH = Path("dataset/gov_myscheme/text_data/25-ciss copy.pdf")

text = extract_text_from_pdf(PDF_PATH)

# -------------------------------
# Create Prompt
# -------------------------------

prompt = f"""
{EXTRACTION_PROMPT}

DOCUMENT:

{text}
"""

print("Sending document to Gemini...")

# -------------------------------
# Gemini Request
# -------------------------------

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
    config={
        "response_mime_type": "application/json"
    }
)

# -------------------------------
# Save JSON
# -------------------------------

output_dir = Path("backend/json_output")
output_dir.mkdir(exist_ok=True)

output_file = output_dir / f"{PDF_PATH.stem}.json"

json_data = json.loads(response.text)

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(json_data, f, indent=4, ensure_ascii=False)

print(f"\nJSON saved to:\n{output_file}")'''
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from postprocess import clean_json
from extract_text import extract_text_from_pdf
from preprocess import preprocess_text
from prompts import EXTRACTION_PROMPT
from schema import Scheme

# =====================================================
# Load Environment Variables
# =====================================================

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("❌ GEMINI_API_KEY not found in .env file")

# =====================================================
# Initialize Gemini Client
# =====================================================

client = genai.Client(api_key=API_KEY)

# =====================================================
# PDF Path
# =====================================================

PDF_PATH = Path("dataset/gov_myscheme/text_data/25-ciss copy.pdf")

if not PDF_PATH.exists():
    raise FileNotFoundError(f"❌ PDF not found: {PDF_PATH}")

# =====================================================
# Extract Text
# =====================================================

print("=" * 60)
print("📄 STEP 1: Extracting text from PDF...")
print("=" * 60)

raw_text = extract_text_from_pdf(str(PDF_PATH))

print(f"✅ Extracted {len(raw_text)} characters")

# =====================================================
# Preprocess Text
# =====================================================

print("\n" + "=" * 60)
print("🧹 STEP 2: Preprocessing extracted text...")
print("=" * 60)

clean_text = preprocess_text(raw_text)

print(f"✅ Cleaned text contains {len(clean_text)} characters")

# =====================================================
# Create Prompt
# =====================================================

prompt = f"""
{EXTRACTION_PROMPT}

--------------------------------------------------
DOCUMENT STARTS HERE
--------------------------------------------------

{clean_text}

--------------------------------------------------
DOCUMENT ENDS HERE
--------------------------------------------------
"""

# =====================================================
# Send to Gemini
# =====================================================

print("\n" + "=" * 60)
print("🤖 STEP 3: Sending document to Gemini...")
print("=" * 60)

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
    config={
        "response_mime_type": "application/json",
        "response_schema": Scheme,
        "temperature": 0.1,
    },
)

print("✅ Gemini response received!")

# =====================================================
# Validate JSON
# =====================================================

print("\n" + "=" * 60)
print("🔍 STEP 4: Validating JSON...")
print("=" * 60)

scheme = Scheme.model_validate_json(response.text)
cleaned_json = clean_json(scheme.model_dump())

print("✅ JSON validation successful!")

# =====================================================
# Create Output Folder
# =====================================================

OUTPUT_DIR = Path("backend/json_output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / f"{PDF_PATH.stem}.json"

# =====================================================
# Save JSON
# =====================================================

print("\n" + "=" * 60)
print("💾 STEP 5: Saving JSON...")
print("=" * 60)

import json

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(
        cleaned_json,
        f,
        indent=4,
        ensure_ascii=False
    )

print("✅ JSON saved successfully!")

print("\n" + "=" * 60)
print("🎉 EXTRACTION COMPLETED SUCCESSFULLY")
print("=" * 60)
print(f"📂 Output File : {OUTPUT_FILE.resolve()}")
print("=" * 60)