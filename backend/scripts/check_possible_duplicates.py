import re
from pathlib import Path
from collections import defaultdict

# =====================================================
# Folder to scan
# =====================================================

PDF_FOLDER = Path("dataset/gov_myscheme/unique_pdfs")

# =====================================================
# Normalize filename
# =====================================================

def normalize_filename(filename: str) -> str:
    """
    Remove common duplicate suffixes.
    """

    name = Path(filename).stem.lower()

    patterns = [
        r"\s+copy$",
        r"\s+\(\d+\)$",
        r"\s*-\s*copy$",
        r"_copy$",
        r"-copy$",
        r"\scopy\s\d+$",
    ]

    for pattern in patterns:
        name = re.sub(pattern, "", name)

    return name.strip()

# =====================================================
# Group files
# =====================================================

groups = defaultdict(list)

for pdf in sorted(PDF_FOLDER.glob("*.pdf")):
    key = normalize_filename(pdf.name)
    groups[key].append(pdf.name)

duplicates = {
    key: files
    for key, files in groups.items()
    if len(files) > 1
}

# =====================================================
# Report
# =====================================================

print("=" * 70)
print("Possible Duplicate Report")
print("=" * 70)

if not duplicates:
    print("✅ No possible duplicate filenames found.")
else:

    count = 0

    for key, files in duplicates.items():

        count += len(files) - 1

        print("\n" + "-" * 60)
        print(f"Group : {key}")

        for file in files:
            print("   ", file)

    print("\n" + "=" * 70)
    print(f"Duplicate Groups : {len(duplicates)}")
    print(f"Possible Duplicates : {count}")