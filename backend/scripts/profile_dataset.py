from pathlib import Path
import fitz  # PyMuPDF
import pandas as pd

# ------------------------------------
# Configuration
# ------------------------------------

PDF_FOLDER = Path("dataset/gov_myscheme/text_data")
REPORT_FOLDER = Path("dataset/reports")
REPORT_FILE = REPORT_FOLDER / "dataset_profile.csv"
SUMMARY_FILE = REPORT_FOLDER / "summary.txt"


# ------------------------------------
# Find all PDFs
# ------------------------------------

def get_pdf_files():
    return sorted(PDF_FOLDER.glob("*.pdf"))


# ------------------------------------
# Analyze one PDF
# ------------------------------------

def analyze_pdf(pdf_path):
    try:
        doc = fitz.open(pdf_path)

        pages = len(doc)
        file_size_kb = round(pdf_path.stat().st_size / 1024, 2)

        full_text = ""

        for page in doc:
            full_text += page.get_text()

        doc.close()

        character_count = len(full_text)
        word_count = len(full_text.split())
        has_text = character_count > 0

        return {
            "file_name": pdf_path.name,
            "pages": pages,
            "file_size_kb": file_size_kb,
            "has_text": has_text,
            "word_count": word_count,
            "character_count": character_count,
            "status": "Valid",
            "error": ""
        }

    except Exception as e:
        return {
            "file_name": pdf_path.name,
            "pages": 0,
            "file_size_kb": 0,
            "has_text": False,
            "word_count": 0,
            "character_count": 0,
            "status": "Corrupted",
            "error": str(e)
        }


# ------------------------------------
# Save CSV Report
# ------------------------------------

def save_report(results):
    REPORT_FOLDER.mkdir(exist_ok=True)

    df = pd.DataFrame(results)

    df.to_csv(REPORT_FILE, index=False)

    save_summary(df)

    print(f"\n✅ CSV Report saved to:")
    print(REPORT_FILE)


# ------------------------------------
# Save Summary Report
# ------------------------------------

def save_summary(df):

    valid_df = df[df["status"] == "Valid"]

    total_pdfs = len(df)
    valid_pdfs = len(valid_df)
    corrupted_pdfs = total_pdfs - valid_pdfs

    pdfs_with_text = valid_df["has_text"].sum()
    pdfs_without_text = valid_pdfs - pdfs_with_text

    total_pages = valid_df["pages"].sum()
    avg_pages = valid_df["pages"].mean()

    max_pages = valid_df["pages"].max()
    min_pages = valid_df["pages"].min()

    total_words = valid_df["word_count"].sum()
    avg_words = valid_df["word_count"].mean()

    total_characters = valid_df["character_count"].sum()
    avg_characters = valid_df["character_count"].mean()

    largest_pdf = valid_df.loc[valid_df["word_count"].idxmax()]
    smallest_pdf = valid_df.loc[valid_df["word_count"].idxmin()]

    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:

        f.write("=" * 50 + "\n")
        f.write("           DATASET PROFILE SUMMARY\n")
        f.write("=" * 50 + "\n\n")

        f.write(f"Total PDFs             : {total_pdfs}\n")
        f.write(f"Valid PDFs             : {valid_pdfs}\n")
        f.write(f"Corrupted PDFs         : {corrupted_pdfs}\n\n")

        f.write(f"PDFs With Text         : {pdfs_with_text}\n")
        f.write(f"PDFs Without Text      : {pdfs_without_text}\n\n")

        f.write(f"Total Pages            : {total_pages}\n")
        f.write(f"Average Pages          : {avg_pages:.2f}\n")
        f.write(f"Maximum Pages          : {max_pages}\n")
        f.write(f"Minimum Pages          : {min_pages}\n\n")

        f.write(f"Total Words            : {total_words}\n")
        f.write(f"Average Words/PDF      : {avg_words:.2f}\n\n")

        f.write(f"Total Characters       : {total_characters}\n")
        f.write(f"Average Characters/PDF : {avg_characters:.2f}\n\n")

        f.write(f"Largest PDF            : {largest_pdf['file_name']}\n")
        f.write(f"Smallest PDF           : {smallest_pdf['file_name']}\n")

        f.write("\n" + "=" * 50)

    print("\n✅ Summary Report saved to:")
    print(SUMMARY_FILE)


# ------------------------------------
# Main
# ------------------------------------

def main():

    pdf_files = get_pdf_files()

    print(f"\nFound {len(pdf_files)} PDF files.\n")

    results = []

    for pdf in pdf_files:
        results.append(analyze_pdf(pdf))

    save_report(results)

    print("\n🎉 Dataset profiling completed successfully!")


if __name__ == "__main__":
    main()