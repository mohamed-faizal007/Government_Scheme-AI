from pathlib import Path
import fitz
import json
from tqdm import tqdm

# =====================================================
# Configuration
# =====================================================

PDF_FOLDER = Path("dataset/gov_myscheme/text_data")
OUTPUT_FOLDER = Path("dataset/extracted_text")

OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)


# =====================================================
# Extract text from one PDF
# =====================================================

def extract_pdf(pdf_path):

    document = fitz.open(pdf_path)

    full_text = ""

    for page in document:
        full_text += page.get_text()

    pages = len(document)

    document.close()

    return {
        "file_name": pdf_path.name,
        "file_code": pdf_path.stem,
        "pages": pages,
        "character_count": len(full_text),
        "word_count": len(full_text.split()),
        "text": full_text
    }


# =====================================================
# Save JSON
# =====================================================

def save_json(data):

    output_path = OUTPUT_FOLDER / f"{data['file_code']}.json"

    with open(output_path, "w", encoding="utf-8") as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=4
        )


# =====================================================
# Main
# =====================================================

def main():

    pdf_files = sorted(PDF_FOLDER.glob("*.pdf"))

    print(f"\nFound {len(pdf_files)} PDF files.\n")

    success = 0
    failed = 0

    for pdf in tqdm(pdf_files, desc="Extracting"):

        try:

            data = extract_pdf(pdf)

            save_json(data)

            success += 1

        except Exception as e:

            failed += 1

            print(f"\nFailed : {pdf.name}")
            print(e)

    print("\n==============================")
    print("Extraction Completed")
    print("==============================")
    print(f"Successful : {success}")
    print(f"Failed     : {failed}")
    print("==============================")


if __name__ == "__main__":
    main()