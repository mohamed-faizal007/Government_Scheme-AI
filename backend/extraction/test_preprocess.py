from extract_text import extract_text_from_pdf
from preprocess import preprocess_text

pdf_path = "dataset/gov_myscheme/text_data/25-ciss copy.pdf"

raw_text = extract_text_from_pdf(pdf_path)

clean_text = preprocess_text(raw_text)

print("=" * 80)
print("RAW TEXT")
print("=" * 80)
print(raw_text[:1500])

print("\n\n")

print("=" * 80)
print("CLEAN TEXT")
print("=" * 80)
print(clean_text[:1500])