"""Text extraction from uploaded documents. Tries PyMuPDF first (fast, exact
for digital PDFs); falls back to PaddleOCR only when the digital extraction
comes back too short to be useful (scanned/image-only PDFs).
Run test: python -m chatbot.backend.documents.ocr <path-to-pdf>  (from repo root)
"""
import logging

import pymupdf

logger = logging.getLogger(__name__)

MIN_TEXT_LENGTH = 100

_paddle_ocr = None


def _get_paddle_ocr():
    global _paddle_ocr
    if _paddle_ocr is None:
        from paddleocr import PaddleOCR

        _paddle_ocr = PaddleOCR(use_angle_cls=True, lang="en")
    return _paddle_ocr


def _extract_with_pymupdf(file_path: str) -> str:
    text_parts = []
    with pymupdf.open(file_path) as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n".join(text_parts).strip()


def _extract_with_paddleocr(file_path: str) -> tuple[str, float]:
    from pdf2image import convert_from_path

    images = convert_from_path(file_path)
    ocr = _get_paddle_ocr()

    text_parts = []
    confidences = []
    for image in images:
        result = ocr.ocr(image.__array__() if hasattr(image, "__array__") else image, cls=True)
        for page_result in result or []:
            for line in page_result or []:
                _, (line_text, line_conf) = line
                text_parts.append(line_text)
                confidences.append(line_conf)

    text = "\n".join(text_parts).strip()
    confidence = sum(confidences) / len(confidences) if confidences else 0.0
    return text, confidence


def extract_text(file_path: str) -> dict:
    text = _extract_with_pymupdf(file_path)

    if len(text) >= MIN_TEXT_LENGTH:
        logger.info("ocr_method=pymupdf chars=%d", len(text))
        return {"text": text, "method": "pymupdf", "confidence": 1.0}

    logger.info("ocr_method=pymupdf_insufficient chars=%d falling_back_to_paddleocr", len(text))
    text, confidence = _extract_with_paddleocr(file_path)
    logger.info("ocr_method=paddleocr chars=%d confidence=%.2f", len(text), confidence)
    return {"text": text, "method": "paddleocr", "confidence": confidence}


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python -m chatbot.backend.documents.ocr <path-to-pdf>")
        sys.exit(1)

    result = extract_text(sys.argv[1])
    print(f"method={result['method']} confidence={result['confidence']:.2f}")
    print(result["text"][:500])
