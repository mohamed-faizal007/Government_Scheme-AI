import json
import sys
import time
from pathlib import Path

from openai import OpenAI


# ==========================================================
# CONFIGURATION
# ==========================================================
# PDF stem (matching the safe_stem test_docling.py wrote its .md as) can
# be passed as an argv, so this can be run across multiple sample PDFs
# for pipeline comparison. Defaults to the original sample.

PDF_STEM = sys.argv[1] if len(sys.argv) > 1 else "25-ciss_copy"

# Docling-generated Markdown file
MARKDOWN_FILE = Path(
    f"dataset/gov_myscheme/docling_test/{PDF_STEM}.md"
)

# Where we will save Qwen's JSON output
OUTPUT_DIR = Path(
    "dataset/gov_myscheme/docling_test"
)

OUTPUT_FILE = OUTPUT_DIR / f"{PDF_STEM}_qwen.json"

# Local Ollama model
MODEL = "qwen2.5:3b"

# Limit for this first experiment.
# We will remove/adjust this after testing.
MAX_INPUT_CHARS = 30000


# ==========================================================
# CHECK INPUT FILE
# ==========================================================

if not MARKDOWN_FILE.exists():
    raise FileNotFoundError(
        f"\n❌ Docling output not found:\n"
        f"{MARKDOWN_FILE.resolve()}\n\n"
        f"Run test_docling.py first."
    )


# ==========================================================
# READ DOCLING OUTPUT
# ==========================================================

print("=" * 80)
print("DOCLING → QWEN TEST")
print("=" * 80)

print(
    f"\nDocling file:\n"
    f"{MARKDOWN_FILE.resolve()}"
)

text = MARKDOWN_FILE.read_text(
    encoding="utf-8"
)

print(
    f"\nCharacters extracted by Docling: "
    f"{len(text):,}"
)


# ==========================================================
# LIMIT INPUT FOR FIRST TEST
# ==========================================================

if len(text) > MAX_INPUT_CHARS:

    print(
        f"\n⚠️ Document contains more than "
        f"{MAX_INPUT_CHARS:,} characters."
    )

    print(
        f"Using the first "
        f"{MAX_INPUT_CHARS:,} characters for this test."
    )

    text = text[:MAX_INPUT_CHARS]


# ==========================================================
# PROMPT
# ==========================================================

prompt = f"""
You are an information extraction system for
Indian government welfare scheme documents.

Your task is to extract factual information from the
provided document and return ONLY valid JSON.

The document may contain webpage noise such as:

- Sign In
- Sign Out
- Cancel
- Back
- Apply Now
- Check Eligibility
- Something went wrong
- navigation menus
- footer text
- duplicated content
- encoding errors
- HTML artifacts

IGNORE these webpage artifacts.

Focus only on the actual government scheme information.

Do NOT invent information.

If information for a field is not available,
return null or an empty list.

Use this exact JSON structure:

{{
    "scheme_name": null,

    "description": null,

    "objectives": [],

    "benefits": [],

    "eligibility": [],

    "exclusions": [],

    "application_process": [],

    "documents_required": [],

    "faqs": [],

    "sources": []
}}

IMPORTANT RULES:

1. Return ONLY JSON.
2. Do not use Markdown code fences.
3. Do not provide explanations outside the JSON.
4. Do not hallucinate information.
5. Preserve important numerical values.
6. Preserve percentages, amounts, dates and conditions.
7. Preserve eligibility restrictions.
8. If the document uses different headings,
   map them to the closest field.
9. Ignore website navigation and UI text.
10. If a section is genuinely absent, use [] or null.
11. Keep the extracted information factual and concise.

DOCUMENT START
-------------------------

{text}

DOCUMENT END
-------------------------
"""


# ==========================================================
# CONNECT TO OLLAMA
# ==========================================================

print("\nConnecting to Ollama...")

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)


# ==========================================================
# SEND TO QWEN
# ==========================================================

print(
    f"Sending document to "
    f"{MODEL}..."
)

start_time = time.time()

response = client.chat.completions.create(
    model=MODEL,
    messages=[
        {
            "role": "user",
            "content": prompt,
        }
    ],
    temperature=0.1,
)

elapsed = time.time() - start_time


# ==========================================================
# GET RESPONSE
# ==========================================================

raw_response = response.choices[0].message.content

print(
    f"\n✅ Qwen response received."
)

print(
    f"Processing time: "
    f"{elapsed:.2f} seconds"
)

print("\nRAW QWEN RESPONSE")
print("=" * 80)
print(raw_response)
print("=" * 80)


# ==========================================================
# CLEAN POSSIBLE MARKDOWN FENCES
# ==========================================================

clean_response = raw_response.strip()

if clean_response.startswith("```json"):
    clean_response = clean_response[7:]

elif clean_response.startswith("```"):
    clean_response = clean_response[3:]


if clean_response.endswith("```"):
    clean_response = clean_response[:-3]


clean_response = clean_response.strip()


# ==========================================================
# VALIDATE JSON
# ==========================================================

print("\nValidating JSON...")

try:

    json_data = json.loads(
        clean_response
    )

except json.JSONDecodeError as e:

    print("\n" + "=" * 80)
    print("❌ INVALID JSON")
    print("=" * 80)

    print(
        f"\nJSON error:\n{e}"
    )

    print(
        "\nThe Qwen response was not valid JSON."
    )

    print(
        "We will fix this before building "
        "the batch pipeline."
    )

    raise


# ==========================================================
# CHECK EXPECTED FIELDS
# ==========================================================

expected_fields = [
    "scheme_name",
    "description",
    "objectives",
    "benefits",
    "eligibility",
    "exclusions",
    "application_process",
    "documents_required",
    "faqs",
    "sources",
]

missing_fields = [
    field
    for field in expected_fields
    if field not in json_data
]


if missing_fields:

    print("\n⚠️ Missing fields:")
    for field in missing_fields:
        print(f"   - {field}")

else:

    print(
        "\n✅ All expected JSON fields are present."
    )


# ==========================================================
# SAVE JSON
# ==========================================================

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        json_data,
        f,
        indent=4,
        ensure_ascii=False
    )


# ==========================================================
# FINAL RESULT
# ==========================================================

print("\n" + "=" * 80)
print("✅ DOCLING → QWEN TEST COMPLETE")
print("=" * 80)

print(
    f"\nJSON saved to:\n"
    f"{OUTPUT_FILE.resolve()}"
)

print(
    f"\nProcessing time:"
    f" {elapsed:.2f} seconds"
)

print("\nNext step:")
print(
    "Inspect 25-ciss_qwen.json and compare "
    "the extracted information with the original PDF."
)

print("=" * 80)