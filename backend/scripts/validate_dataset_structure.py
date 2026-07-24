from pathlib import Path
import fitz
import random

# -----------------------------
# Configuration
# -----------------------------

PDF_FOLDER = Path("dataset/gov_myscheme/text_data")
REPORT_FILE = Path("dataset/reports/dataset_structure_validation.txt")

SAMPLE_SIZE = 25


# -----------------------------
# Extract first lines
# -----------------------------

def extract_preview(pdf_path):

    doc = fitz.open(pdf_path)

    text = ""

    for page in doc:
        text += page.get_text()

    doc.close()

    lines = []

    for line in text.splitlines():

        line = line.strip()

        if line:
            lines.append(line)

    return lines[:30]


# -----------------------------
# Main
# -----------------------------

def main():

    pdfs = list(PDF_FOLDER.glob("*.pdf"))

    random.seed(42)          # Fixed sample every run
    sample = random.sample(pdfs, SAMPLE_SIZE)

    with open(REPORT_FILE, "w", encoding="utf-8") as report:

        report.write("=" * 80 + "\n")
        report.write("DATASET STRUCTURE VALIDATION REPORT\n")
        report.write("=" * 80 + "\n\n")

        for i, pdf in enumerate(sample, start=1):

            report.write(f"\n{'='*80}\n")
            report.write(f"Sample {i}\n")
            report.write(f"{'='*80}\n")

            report.write(f"Filename : {pdf.name}\n\n")

            try:

                preview = extract_preview(pdf)

                for line in preview:
                    report.write(line + "\n")

            except Exception as e:

                report.write(f"ERROR : {e}\n")

            report.write("\n")

    print("✅ Validation report generated successfully.")
    print(REPORT_FILE)


if __name__ == "__main__":
    main()