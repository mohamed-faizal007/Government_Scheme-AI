# Resume Note

State as of 2026-10-21:

- Branch: `main`
- PDFs processed: 2,066 / 2,066 (0 failed, 0 schema-invalid; 2,339 Unstructured pages used in total), in `dataset/gov_myscheme/test_output_unstructured/`
- MongoDB (`gov_scheme_ai.schemes`): 2,066 documents. ChromaDB (`schemes`): 7,528 chunks (8,264 minus 736 content-free description chunks; every scheme keeps at least 3).
- Re-evaluated 2026-10-21 after all fixes: eligibility 95%, out-of-scope decline 10/10 (8 router, 2 citation guard), citation rate 28% (14/50), retrieval spot-check 7/10, average time 3.7s, 0 Groq 413 failures, answers 20b 21 / 120b 3 / Ollama 0. See the six-column table in `PROJECT_HANDOFF.md`.
- Column 7 (exact-name prompt line + `SCHEME_CHAR_CAP` 2,500) is kept and committed. Result: citation 32% (16/50), spot-check 7/10, average 4.4s (2.3s without q29, 110s on Ollama fallback), 0 413s, 24 rate-limit events, answers 20b 13 / 120b 10 / Ollama 1; q3, q22, q24 answered, q44 flipped to declined. Not solved: q4, q5, q26 and q28 are still open.
- Done this session: token budget + 413 retry, pop-up text stripped from descriptions, 73 file-name scheme names recovered, content-free description chunks skipped, citation-guard name normalisation, Romanized-Hindi router patterns (scheme word required).

- 2026-10-27: follow-up routing / session scheme memory / language rule / sentence-level translation committed (406e727). Gemini understanding layer added in `chatbot/backend/nlu/` (see "Gemini understanding layer" in `PROJECT_HANDOFF.md`): env `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_MODEL_FALLBACK`, `GEMINI_SESSION_CAP` (20), `GEMINI_DAILY_CAP` (200 placeholder; set to ~80% of the AI Studio limit). Called only for messages the router leaves out_of_scope; on any failure (no key, 429/503/504, 8 s cutoff, invalid JSON, caps) the old refusal is used. **PENDING: the live Gemini tests** (Gemini returned 503/504 for most calls on 2026-10-27). When it is healthy run `PYTHONPATH=. python -m chatbot.evaluation.test_nlu_layer` from the repo root (the 2 `test_live_*` tests print PENDING while it is down), then `python -m chatbot.evaluation.eval_rag`; also set `GEMINI_DAILY_CAP` in `chatbot/.env` from AI Studio. Typo tolerance (`router/typos.py`), model order, circuit breaker are in `PROJECT_HANDOFF.md`.

Full context: `PROJECT_HANDOFF.md`. Eval results: `chatbot/evaluation/EVAL_REPORT.md`.

## State as of 2026-10-28 (demo-speed work, committed)

**Done:**
- Provider chain Groq 20b -> Groq 120b -> Gemini (GEMINI_MODEL, GEMINI_MODEL_FALLBACK) -> Ollama (20 s limit): `llm/chain.py`, `llm/limits.py`, rewritten `groq_provider.py`, `gemini_provider.py`, `ollama_provider.py`, `factory.py`. A 429 moves on with no sleep; a daily-limit 429 blocks that model until its reset. The citation guard applies to every provider. When all fail the user sees the fixed "busy, retry in a minute" text (en/hi/ta, `BUSY_MESSAGES` in `rag/generator.py`).
- Warm-up at start (`backend/warmup.py`, run in `lifespan`): embedding model, Chroma, MongoDB name index, hi/ta translators, one dummy retrieval + translation.
- Answer cache (`backend/cache/`, `ANSWER_CACHE=on/off`, file `chatbot/data/answer_cache.json`, 500 entries, 24 h; clear with `python -m chatbot.backend.cache.clear_cache`, then restart). Only guard-passed answers with sources; never refusals, errors, busy text, eligibility turns, anything with a profile, follow-ups or NLU-rewritten turns.
- Rule-based greetings/thanks in en/hi/ta (`nlu/smalltalk.py`): no LLM call.
- Gemini understanding layer (`nlu/`), typo tolerance (`router/typos.py`), scheme-name index changes.
- Live Gemini tests now SKIP (with a reason) instead of failing when a call times out or returns 429/503/504.

**Verified in the previous session (2026-10-27/28):**
- `test_followup_regression`: 8/8 passed.
- `test_nlu_layer`: 30 passed, 1 failed, 1 skipped. The failure was one live Gemini call per run hitting the 8 s cutoff; the skip was the live end-to-end test.
- Smoke test (6 queries x2): English farmers 2.40 s then 0.00 s (cache); Hindi 4.35 s then 0.00 s; Tamil 7.48 s then 0.00 s; follow-up 1.85 s / 2.49 s (not cached by design); out-of-scope 3.25 s / 1.97 s, declined; "hi" 0.00 s. Cache hits identical answer and sources.
- Port stays closed until warm-up finishes (checked against a real server), and WebSocket "hi" / "நன்றி" answered correctly.
- Warm-up itself took 15-27 s.

**NOT yet verified:**
- The live 30-message Gemini test on a healthy day: latency, JSON validity and injection handling (it had 29/30 per run, with one 8 s timeout each time).
- `GEMINI_DAILY_CAP` is still the 200 placeholder; set it from AI Studio.
- Nothing was re-run for the commit that contains this note (static checks only: py_compile, pytest --collect-only).

**Startup:** about 2.5 minutes before the port opens (about 2 minutes of imports and model loading, then 15-27 s warm-up). The UI cannot connect until then.

**Resume commands** (repo root, Git Bash):
```
venv/Scripts/python.exe -m chatbot.backend.cache.clear_cache
venv/Scripts/python.exe -m uvicorn chatbot.backend.api.main:app --port 8000   # watch the "warm-up:" log lines
PYTHONPATH=. venv/Scripts/python.exe -m chatbot.evaluation.test_nlu_layer     # calls Groq and Gemini
PYTHONPATH=. venv/Scripts/python.exe -m chatbot.evaluation.test_followup_regression   # calls Groq
```
Open item: fuzzy (edit-distance) typo matching in `router/typos.py`.

## State as of 2026-10-28 (Gemini as primary generator, NOT committed)

- New chain: Gemini (`GEMINI_MODEL`, `GEMINI_MODEL_FALLBACK`) -> Groq 20b -> Groq 120b -> Ollama. Switch with env `GENERATION_PRIMARY=gemini|groq` (default gemini; `groq` keeps the old order Groq 20b -> 120b -> Gemini -> Ollama). Gemini generation timeout is `GEMINI_GEN_TIMEOUT` (6 s); a timeout/429/503/504 goes to Groq at once. Understanding and generation share one daily counter (`GEMINI_DAILY_CAP`) and one circuit breaker. Details: "Answer generation chain" in `PROJECT_HANDOFF.md`.
- Verified: offline fake-based tests only (`chatbot/evaluation/test_generation_chain_offline.py`), no live call.
- **NOT verified live:** Gemini as the primary generator. Its latency, citation rate and answer quality compared with Groq are unknown. Before relying on it, run `eval_rag` with `GENERATION_PRIMARY=gemini` and with `groq` and compare; if Gemini is worse, set `GENERATION_PRIMARY=groq`.

## Pending work

1. Make the citation guard tolerate model abbreviations of scheme names ("Amma Two Wheeler Scheme", "(AAN)"); re-run the eval.
2. Recover the 13 remaining truncated scheme names (`Dr. B.`, `E.`, `'`, ...) from the source PDFs, as was done for the 73; 67 other-section chunks are content-free and 84 chunks still contain the pop-up sentence.
3. Tamil retrieval for queries that name a specific scheme (q5, q6, q18, q26; q6 now answers with a wrong scheme).
4. Sync pipeline source: build the Playwright scraper, or register a MyScheme API key.
5. Feedback buttons in the hero widget.

Never modify `backend/extraction/` pipeline originals (`batch_extract.py`, `preprocess.py`) or `json_output/`.
