# Resume Note

State as of 2026-10-14:

- Branch: `main`, last commit `01f939a`
- PDFs processed: 488 / 2,066 (1,578 remain), in `dataset/gov_myscheme/test_output_unstructured/`
- MongoDB (`gov_scheme_ai.schemes`): 488 documents. ChromaDB (`schemes`): 1,952 chunks.

Full context: `PROJECT_HANDOFF.md`. Eval results: `chatbot/evaluation/EVAL_REPORT.md`.

## Pending work

1. Process the remaining PDFs, 200 per batch.
2. Sync pipeline source: build the Playwright scraper, or register a MyScheme API key.
3. Tamil retrieval for queries that name a specific scheme.
4. Feedback buttons in the hero widget.
5. After all PDFs are processed: re-ingest (`load_mongo.py`, `load_chroma.py`), re-run `eval_rag.py` and `eval_eligibility.py`, update the report.

## Batch command

Check `dataset/gov_myscheme/logs/page_usage.log` first (Unstructured limit: 15,000 pages/month), then from the repo root:

    python backend/extraction/batch_run_200.py

It is idempotent and safe to stop and resume. Never modify `backend/extraction/` pipeline originals (`batch_extract.py`, `preprocess.py`) or `json_output/`.
