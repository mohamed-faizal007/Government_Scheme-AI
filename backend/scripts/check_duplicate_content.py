import hashlib
import re
from pathlib import Path
from collections import defaultdict

import fitz  # PyMuPDF

# =====================================================
# Folder
# =====================================================

PDF_FOLDER = Path("dataset/gov_myscheme/unique_pdfs")

# =====================================================
# Extract Text
# =====================================================

def extract_text(pdf_path: Path):

    doc = fitz.open(pdf_path)

    text = ""

    for page in doc:
        text += page.get_text()

    doc.close()

    return text

# =====================================================
# Normalize Text
# =====================================================

def normalize_text(text):

    text = text.lower()

    text = re.sub(r"\s+", " ", text)

    return text.strip()

# =====================================================
# Hash Map
# =====================================================

content_map = defaultdict(list)

pdfs = sorted(PDF_FOLDER.glob("*.pdf"))

print(f"\nScanning {len(pdfs)} PDFs...\n")

for pdf in pdfs:

    try:

        text = extract_text(pdf)

        text = normalize_text(text)

        content_hash = hashlib.sha256(
            text.encode("utf-8")
        ).hexdigest()

        content_map[content_hash].append(pdf.name)

    except Exception:

        print(f"Could not read {pdf.name}")

# =====================================================
# Report
# =====================================================

duplicate_groups = []

for files in content_map.values():

    if len(files) > 1:
        duplicate_groups.append(files)

print("=" * 70)

print("CONTENT DUPLICATE REPORT")

print("=" * 70)

if not duplicate_groups:

    print("✅ No duplicate document contents found.")

else:

    total = 0

    for group in duplicate_groups:

        total += len(group) - 1

        print("\n")

        for file in group:
            print(file)

    print("\n")

    print("=" * 70)

    print(f"Duplicate Groups : {len(duplicate_groups)}")

    print(f"Duplicate Files  : {total}")