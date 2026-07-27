import fitz
from pathlib import Path


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from all pages of a PDF."""

    document = fitz.open(pdf_path)

    text = []

    for page in document:
        text.append(page.get_text())

    document.close()

    return "\n".join(text)


if __name__ == "__main__":
    pdf = Path("dataset/gov_myscheme/text_data/25-ciss copy.pdf")

    extracted_text = extract_text_from_pdf(pdf)

    print(extracted_text[:3000])