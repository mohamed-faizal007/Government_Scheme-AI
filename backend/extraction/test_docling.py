import sys
from pathlib import Path
import time

from docling.document_converter import DocumentConverter


# ==========================================================
# CONFIGURATION
# ==========================================================
# PDF stem (filename without .pdf) can be passed as an argv, so this can
# be run across multiple sample PDFs for pipeline comparison. Defaults
# to the original sample for backward compatibility.

PDF_STEM = sys.argv[1] if len(sys.argv) > 1 else "25-ciss copy"

PDF_PATH = Path(
    f"dataset/gov_myscheme/unique_pdfs/{PDF_STEM}.pdf"
)

OUTPUT_DIR = Path(
    "dataset/gov_myscheme/docling_test"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ==========================================================
# CHECK PDF
# ==========================================================

if not PDF_PATH.exists():
    raise FileNotFoundError(
        f"PDF not found:\n{PDF_PATH.resolve()}"
    )


# ==========================================================
# INITIALIZE DOCLING
# ==========================================================

print("=" * 80)
print("DOCLING TEST")
print("=" * 80)

print(f"PDF: {PDF_PATH.resolve()}")

print("\nInitializing Docling...")

converter = DocumentConverter()


# ==========================================================
# CONVERT PDF
# ==========================================================

print("\nParsing PDF...")

start_time = time.time()

result = converter.convert(
    str(PDF_PATH)
)

elapsed = time.time() - start_time

print(
    f"\nDocling conversion completed in "
    f"{elapsed:.2f} seconds."
)


# ==========================================================
# EXPORT MARKDOWN
# ==========================================================

markdown = result.document.export_to_markdown()

safe_stem = PDF_STEM.replace(" ", "_")

markdown_file = OUTPUT_DIR / f"{safe_stem}.md"

markdown_file.write_text(
    markdown,
    encoding="utf-8"
)


# ==========================================================
# EXPORT TEXT
# ==========================================================

text = result.document.export_to_text()

text_file = OUTPUT_DIR / f"{safe_stem}.txt"

text_file.write_text(
    text,
    encoding="utf-8"
)


# ==========================================================
# SUMMARY
# ==========================================================

print("\n" + "=" * 80)
print("RESULT")
print("=" * 80)

print(f"Markdown file : {markdown_file.resolve()}")
print(f"Text file     : {text_file.resolve()}")
print(f"Characters    : {len(markdown):,}")

print("\nFirst 2,000 characters:")
print("-" * 80)

print(markdown[:2000])

print("\n" + "=" * 80)
print("DOCLING TEST COMPLETE")
print("=" * 80)