import hashlib
import shutil
from pathlib import Path

# =====================================================
# Paths
# =====================================================

SOURCE_FOLDER = Path("dataset/gov_myscheme/text_data")
DESTINATION_FOLDER = Path("dataset/gov_myscheme/unique_pdfs")

DESTINATION_FOLDER.mkdir(parents=True, exist_ok=True)

# =====================================================
# Calculate SHA256 Hash
# =====================================================

def calculate_hash(file_path: Path) -> str:
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        while chunk := file.read(8192):
            sha256.update(chunk)

    return sha256.hexdigest()

# =====================================================
# Find PDFs
# =====================================================

pdf_files = sorted(SOURCE_FOLDER.glob("*.pdf"))

print("=" * 70)
print(f"Scanning {len(pdf_files)} PDF files...")
print("=" * 70)

hash_map = {}

duplicates = []

unique_count = 0

# =====================================================
# Detect Duplicates
# =====================================================

for pdf in pdf_files:

    file_hash = calculate_hash(pdf)

    if file_hash not in hash_map:

        hash_map[file_hash] = pdf

        shutil.copy2(
            pdf,
            DESTINATION_FOLDER / pdf.name
        )

        unique_count += 1

    else:

        duplicates.append((pdf, hash_map[file_hash]))

# =====================================================
# Save Duplicate Report
# =====================================================

report_path = DESTINATION_FOLDER / "duplicate_report.txt"

with open(report_path, "w", encoding="utf-8") as report:

    report.write("=" * 70 + "\n")
    report.write("Duplicate PDF Report\n")
    report.write("=" * 70 + "\n\n")

    for duplicate, original in duplicates:

        report.write(f"Duplicate : {duplicate.name}\n")
        report.write(f"Original  : {original.name}\n")
        report.write("-" * 60 + "\n")

# =====================================================
# Summary
# =====================================================

print("\n")

print("=" * 70)
print("SUMMARY")
print("=" * 70)

print(f"Total PDFs       : {len(pdf_files)}")
print(f"Unique PDFs      : {unique_count}")
print(f"Duplicate PDFs   : {len(duplicates)}")

print(f"\nUnique PDFs saved to:")
print(DESTINATION_FOLDER.resolve())

print(f"\nDuplicate report:")
print(report_path.resolve())

print("=" * 70)