"""
Manual, single-batch runner: processes the next N (default 200) not-yet-
processed PDFs, alphabetically, then stops. Run it again to process the
next batch -- it re-scans the output folder each time, so already-completed
files are never reprocessed no matter how many times this is run.

Reuses batch_extract_unstructured.py's process_pdf() unmodified -- does not
edit that file. Only writes to test_output_unstructured/; never touches
json_output/ or batch_extract.py.

Usage:
    python batch_run_200.py                  # next 200
    python batch_run_200.py --batch-size 50   # next 50
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from batch_extract_unstructured import PDF_FOLDER, OUTPUT_FOLDER, process_pdf

PAGE_LOG_FILE = Path("dataset/gov_myscheme/logs/page_usage.log")


def read_running_total() -> int:
    """Seed the running page-usage total from the last line of the log,
    so it persists correctly across separate batch runs (this script may
    be invoked many times, each a fresh process)."""

    if not PAGE_LOG_FILE.exists():
        return 0

    last_line = None
    with open(PAGE_LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                last_line = line

    if not last_line:
        return 0

    try:
        return int(last_line.rsplit(",", 1)[-1].strip())
    except ValueError:
        return 0


def log_page_usage(filename: str, pages: int, running_total: int) -> None:
    PAGE_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PAGE_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{filename}, {pages}, {running_total}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=200,
                         help="How many not-yet-processed PDFs to run this time (default: 200)")
    args = parser.parse_args()

    all_pdfs = sorted(PDF_FOLDER.glob("*.pdf"))

    # Scan output folder fresh every run -- a file is "done" purely by the
    # existence of its output JSON, so re-running this script never
    # reprocesses anything already completed, regardless of how many times
    # (or in how many separate batches) it has been run before.
    completed = {p.stem for p in OUTPUT_FOLDER.glob("*.json")}
    unprocessed = [p for p in all_pdfs if p.stem not in completed]

    batch = unprocessed[: args.batch_size]

    print(f"Total PDFs                : {len(all_pdfs)}")
    print(f"Already completed         : {len(completed)}")
    print(f"Unprocessed (before batch): {len(unprocessed)}")
    print(f"This batch size           : {len(batch)}")
    print(f"Output folder             : {OUTPUT_FOLDER.resolve()}")
    print()

    if not batch:
        print("Nothing to do -- all PDFs already have output.")
        return

    processed = 0
    invalid = 0
    failed = 0
    errors = []
    batch_pages = 0
    running_total = read_running_total()
    start = time.time()

    for i, pdf_path in enumerate(batch):
        try:
            result = process_pdf(pdf_path)
        except Exception as exc:
            failed += 1
            errors.append((pdf_path.name, f"{type(exc).__name__}: {exc}"))
            print(f"[{i + 1}/{len(batch)}] FAILED  {pdf_path.name} -> {type(exc).__name__}: {exc}")
            continue

        # Pages are consumed by the Unstructured API call regardless of
        # whether the result later passes schema validation, so log usage
        # for both valid and invalid results.
        pages = result.get("pages_consumed", 0)
        running_total += pages
        batch_pages += pages
        log_page_usage(pdf_path.name, pages, running_total)

        if result["valid"]:
            output_file = OUTPUT_FOLDER / f"{pdf_path.stem}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result["final_json"], f, indent=4, ensure_ascii=False)
            processed += 1
            if (i + 1) % 25 == 0 or i == 0:
                elapsed = time.time() - start
                rate = elapsed / (i + 1)
                eta = rate * (len(batch) - i - 1)
                print(f"[{i + 1}/{len(batch)}] OK      {pdf_path.name}  "
                      f"(elapsed={elapsed / 60:.1f}m, eta={eta / 60:.1f}m, "
                      f"pages_running_total={running_total})")
        else:
            invalid += 1
            errors.append((pdf_path.name, f"schema invalid: {result.get('validation_errors')}"))
            print(f"[{i + 1}/{len(batch)}] INVALID {pdf_path.name} -> {result.get('validation_errors')}")

    elapsed = time.time() - start

    # Recompute remaining-after-batch fresh from disk, not by arithmetic,
    # so it's correct even if some "processed" writes above failed midway.
    completed_after = {p.stem for p in OUTPUT_FOLDER.glob("*.json")}
    remaining_after = len(all_pdfs) - len(completed_after)

    print("\n" + "=" * 80)
    print("BATCH SUMMARY")
    print("=" * 80)
    print(f"Batch size requested   : {args.batch_size}")
    print(f"Attempted this batch   : {len(batch)}")
    print(f"Processed successfully : {processed}")
    print(f"Invalid (schema)       : {invalid}")
    print(f"Failed (exception)     : {failed}")
    print(f"Elapsed                : {elapsed / 60:.1f} minutes")
    print(f"Remaining unprocessed  : {remaining_after} (out of {len(all_pdfs)} total)")
    print(f"Pages consumed (batch) : {batch_pages}")
    print(f"Pages consumed (total) : {running_total}  (free-tier limit: 15,000/month)")
    print(f"Page usage log         : {PAGE_LOG_FILE.resolve()}")
    print()
    if errors:
        print("FAILED / INVALID FILES:")
        for name, err in errors:
            print(f"  {name}: {err}")
    else:
        print("No failures or invalid files this batch.")


if __name__ == "__main__":
    main()
