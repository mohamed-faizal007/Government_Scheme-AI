import os
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from unstructured_client import UnstructuredClient
from unstructured_client.models import operations, shared

load_dotenv()

API_KEY = os.getenv("UNSTRUCTURED_API_KEY")

if not API_KEY:
    raise ValueError("UNSTRUCTURED_API_KEY not found in .env")

_client = UnstructuredClient(api_key_auth=API_KEY)


def partition_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Parse a PDF into structured elements via the hosted Unstructured API
    (strategy="hi_res"). Returns the raw element list (titles, narrative
    text, list items, tables), each a dict with "type", "text", and
    "metadata".

    strategy="fast" was tried first (as originally planned) but produces
    unusable, unspaced body text for this dataset's PDFs (e.g.
    "eligibletoapplyunderthescheme" with zero recoverable word
    boundaries) -- confirmed by direct comparison on the same PDF.
    hi_res preserves correct inter-word spacing throughout, at the cost
    of consuming more of the Unstructured free-tier page budget.
    """

    path = Path(pdf_path)
    content = path.read_bytes()

    request = operations.PartitionRequest(
        partition_parameters=shared.PartitionParameters(
            files=shared.Files(content=content, file_name=path.name),
            strategy=shared.Strategy.HI_RES,
            unique_element_ids=True,
        ),
    )

    response = _client.general.partition(request=request)

    return response.elements or []


def pages_consumed(elements: List[Dict[str, Any]]) -> int:
    """
    Highest page number seen across element metadata -- a proxy for how
    many pages the Unstructured free-tier budget was billed for this PDF.
    """

    pages = [
        el.get("metadata", {}).get("page_number")
        for el in elements
        if el.get("metadata", {}).get("page_number") is not None
    ]

    return max(pages) if pages else 0


if __name__ == "__main__":
    import sys

    pdf = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "dataset/gov_myscheme/unique_pdfs/25-ciss copy.pdf"
    )

    els = partition_pdf(str(pdf))

    print(f"Elements: {len(els)}")
    print(f"Pages consumed: {pages_consumed(els)}")

    for el in els[:15]:
        print(f"- [{el.get('type')}] {(el.get('text') or '')[:80]}")
