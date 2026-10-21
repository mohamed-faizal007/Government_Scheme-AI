# Resume Note

State as of 2026-10-21:

- Branch: `main`
- PDFs processed: 2,066 / 2,066 (0 failed, 0 schema-invalid; 2,339 Unstructured pages used in total), in `dataset/gov_myscheme/test_output_unstructured/`
- MongoDB (`gov_scheme_ai.schemes`): 2,066 documents. ChromaDB (`schemes`): 7,528 chunks (8,264 minus 736 content-free description chunks; every scheme keeps at least 3).
- Re-evaluated 2026-10-21 after all fixes: eligibility 95%, out-of-scope decline 10/10 (8 router, 2 citation guard), citation rate 28% (14/50), retrieval spot-check 7/10, average time 3.7s, 0 Groq 413 failures, answers 20b 21 / 120b 3 / Ollama 0. See the six-column table in `PROJECT_HANDOFF.md`.
- Column 7 (exact-name prompt line + `SCHEME_CHAR_CAP` 2,500) is kept and committed. Result: citation 32% (16/50), spot-check 7/10, average 4.4s (2.3s without q29, 110s on Ollama fallback), 0 413s, 24 rate-limit events, answers 20b 13 / 120b 10 / Ollama 1; q3, q22, q24 answered, q44 flipped to declined. Not solved: q4, q5, q26 and q28 are still open.
- Done this session: token budget + 413 retry, pop-up text stripped from descriptions, 73 file-name scheme names recovered, content-free description chunks skipped, citation-guard name normalisation, Romanized-Hindi router patterns (scheme word required).

Full context: `PROJECT_HANDOFF.md`. Eval results: `chatbot/evaluation/EVAL_REPORT.md`.

## Pending work

1. Make the citation guard tolerate model abbreviations of scheme names ("Amma Two Wheeler Scheme", "(AAN)"); re-run the eval.
2. Recover the 13 remaining truncated scheme names (`Dr. B.`, `E.`, `'`, ...) from the source PDFs, as was done for the 73; 67 other-section chunks are content-free and 84 chunks still contain the pop-up sentence.
3. Tamil retrieval for queries that name a specific scheme (q5, q6, q18, q26; q6 now answers with a wrong scheme).
4. Sync pipeline source: build the Playwright scraper, or register a MyScheme API key.
5. Feedback buttons in the hero widget.

Never modify `backend/extraction/` pipeline originals (`batch_extract.py`, `preprocess.py`) or `json_output/`.
