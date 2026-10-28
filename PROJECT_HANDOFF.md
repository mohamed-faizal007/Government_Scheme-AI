# Government Scheme AI — Project Handoff Document

Last updated: 2026-10-21
Status: Extraction complete (2,066/2,066 PDFs processed), loaded into MongoDB and ChromaDB, and re-evaluated on the full corpus. Chatbot built (backend, frontend, sync pipeline, evaluation).

---

## Project Goal

Convert 2,066 government scheme PDFs into structured, schema-validated JSON files, then build an AI-powered chatbot that can search schemes, check eligibility, verify documents, and respond in English, Tamil, and Hindi.

Full project plan: `PROJECT_PLAN.md`
Chatbot implementation plan: `CHATBOT_IMPLEMENTATION_PROMPT.md`
Pending work reference: `RESUME_LATER.md`

---

## Repository

Local path:
```
C:\Faizal\Government_Scheme-AI
```

GitHub:
```
https://github.com/mohamed-faizal007/Government_Scheme-AI
```

Active branch:
```
main
```

Work is committed directly on `main`.

---

## Current State

### PDF Processing
- Total PDFs: 2,066
- Processed: **2,066 of 2,066** (in `dataset/gov_myscheme/test_output_unstructured/`), completed 2026-10-21
- Failed: 0. Schema-invalid: 0. Unstructured pages used in total: 2,339 (limit 15,000/month)
- MongoDB (`gov_scheme_ai.schemes`): 2,066 documents. ChromaDB (`schemes`): 7,528 chunks (8,264 minus 736 content-free description chunks). "sign out" in scheme names: 0 in both.
- `batch_run_200.py` is idempotent; rerunning it with nothing left prints "Nothing to do"

### Git
- Active branch: `main`
- Last commit before the full-corpus run: `845df5f`; the full-corpus commit follows it on `main`

---

## Extraction Pipeline — What Was Built

### Approach (Current Active — Approach #5)

```
PDF
 ↓
Unstructured Serverless API (strategy="hi_res")
 ↓
insert_boundaries.py  — inserts section delimiters
 ↓
classify_headings.py  — embedding classifier maps headings to 7 categories
 ↓
extract_sections.py   — extracts content verbatim under each heading
 ↓
Pydantic validation (schema.py)
 ↓
JSON output (dataset/gov_myscheme/test_output_unstructured/)
```

No LLM in the extraction pipeline. Fully deterministic.

### Why This Approach
- Gemini (approach #1): worked but hit free quota at 17/2066 PDFs
- Rule-based (approach #2): too fragile for inconsistent headings
- Docling + Qwen (approach #3): slow (~185s/PDF), unresolved bugs
- Docling + Groq (approach #4): ~45 PDFs/day cap, too slow
- Unstructured + embedding classifier (approach #5): chosen — no LLM, no quota, fast

### Files Created (all in `backend/extraction/`)
```
parse_unstructured.py         ← calls Unstructured API
insert_boundaries.py          ← section boundary insertion
classify_headings.py          ← embedding classifier
extract_sections.py           ← content extraction
batch_extract_unstructured.py ← single-file pipeline
batch_run_200.py              ← batch runner (200 at a time, idempotent)
postprocess_faq.py            ← written but NOT used — ignore
```

### Files That Must Never Be Modified
```
batch_extract.py              ← original Gemini pipeline
preprocess.py                 ← original preprocessing
json_output/                  ← original Gemini JSON outputs (17 files)
dataset/gov_myscheme/unique_pdfs/  ← source PDFs
```

Note: JSON outputs live at `dataset/gov_myscheme/test_output_unstructured/` (not a repo-root `test_output_unstructured/`) — use this path everywhere in chatbot code.

---

## Bugs Found and Fixed (do not rediscover these)

### Bug 1 — Footer noise in extracted content (FIXED)
Footer strings like `"No new news and updates available©2024"`, `"(DIC)(MeitY)Government of India®"`, `"Get in touch4th Floor, Electronics Niketan..."` were leaking into objectives and FAQ fields.

Fix: strip 8 known footer strings from raw text before boundary insertion. Required mojibake repair pass (`©` → `Â©`) and distance-bounded gap matching for split strings.

### Bug 2 — Label artifacts in eligibility.conditions (FIXED)
Webpage UI labels (`"Details"`, `"Grant"`, `"Infrastructure"`, scheme name repeated) were appearing as items in `eligibility.conditions`.

Fix: post-extraction filter in `extract_sections.py`. Item is filtered if: ≤3 words AND no digits AND no trailing `./:` AND (Title-Case-shaped OR exact scheme-name match). Tightened after finding "Aadhaar card" would be a false positive under the original rule.

### Bug 3 — Duplicate heading continuation merge (FIXED)
When a heading-vocabulary term appeared twice in a document, the second occurrence split an already-correctly-opened section, causing content truncation.

Fix: in `classify_headings.py`, consecutive matches of the same category are merged rather than split.

### Bug 4 — Nav-bar false section boundaries (FIXED)
Page nav bar (`BackDetailsBenefitsEligibility...`) appeared as glued heading-vocabulary words, opening spurious empty sections. Also `"Check Eligibility"` and `"Apply Now"` button text was firing as heading matches, causing description/objective content to be absorbed into wrong sections.

Fix (3 sub-fixes):
- (a) Strip `"Check Eligibility"` and `"Apply Now"` from raw text before `insert_boundaries()`
- (b) Suppress consecutive heading matches with gap=0 (the tab-list chain)
- (c) Capture orphan content between suppressed chain and next real heading into `overview.description`

### Bug 5 — preprocess.py data corruption (historical, already fixed before this session)
Blind substring removal turned "Engineer" → "ineer". Fixed with regex `\b` word boundary matching.

---

## Known Limitations in Output (accepted, will not be fixed)

These affect `dataset/gov_myscheme/test_output_unstructured/` JSONs. They do not block the chatbot.

| Issue | Frequency | Impact |
|---|---|---|
| FAQ content misclassified into benefits | ~64% of files | Low for RAG — content present, wrong field |
| scheme_name corrupted with UI text | ~5% of files | Medium — handle in MongoDB load |
| objectives field empty | ~80% of files | Low — content is in overview.description |
| Objective text in benefits (a-gainer pattern) | ~9% of files | Low for RAG |
| \ufeff invisible character in label filter | ~1% of files | Very low |
| Glued preamble fragments in eligibility | Small % | Low |

Root cause of FAQ-in-benefits: heading-vocabulary terms like `"financial assistance"` and `"benefits"` appear naturally in FAQ prose, causing the classifier to re-fire inside FAQ content and misroute it. Three structural heuristics were investigated and falsified (proximity clustering, pipeline reordering, content-window length). An LLM post-processing pass (`postprocess_faq.py`) was designed and partially validated but not used — Gemini free tier hit a 20 requests/day RPD cap, and local Qwen was rejected as too unreliable. Accepted as-is for RAG use case where field-level placement does not matter.

**Tamil translation** (Phase 7): argostranslate has no en↔ta model, and Helsinki-NLP has no bilingual ta↔en model. Resolved with the Helsinki-NLP Dravidian models `opus-mt-dra-en` (ta→en, used for retrieval and intent classification) and `opus-mt-en-dra` (en→ta with a `>>tam<<` prefix, used for output). They run locally via `MarianTokenizer`/`MarianMTModel` (the `pipeline("translation")` task was removed in transformers 5.x), load lazily on first use, and fall back to the original text on failure. Scheme names are kept in English in Tamil responses and numbered lists/markdown are preserved (`translate(..., schemes=...)` in `translator.py`). Translation quality is only moderate: structure and names are reliable, but descriptive Tamil prose can be garbled or lose figures.

---

## JSON Output Schema

Every file in `dataset/gov_myscheme/test_output_unstructured/` follows this structure (`backend/extraction/schema.py`):

```json
{
  "metadata": {
    "scheme_name": "...",
    "scheme_type": "",
    "state": "",
    "implementing_department": "",
    "category": ""
  },
  "overview": {
    "description": "...",
    "objectives": [],
    "beneficiaries": []
  },
  "benefits": {
    "financial_assistance": "",
    "other_benefits": []
  },
  "eligibility": {
    "conditions": [],
    "exclusions": []
  },
  "application": {
    "mode": "",
    "documents": [],
    "steps": []
  },
  "support": {
    "official_website": "",
    "helpline": "",
    "important_dates": [],
    "source_links": []
  },
  "faq": [
    {"question": "...", "answer": "..."}
  ],
  "search_metadata": {
    "tags": [],
    "keywords": []
  },
  "notes": ""
}
```

Note: `overview.description` is populated for 100% of files (orphan content capture fix). `overview.objectives` is empty in ~80% of files — use `overview.description` as the primary description field.

---

## Unstructured API

- Strategy: `hi_res` (not `fast` — `fast` produces zero Title elements dataset-wide)
- Free tier: 15,000 pages/month
- Page usage log: `dataset/gov_myscheme/logs/page_usage.log`
- Check before each batch run

---

## Embedding Model (extraction pipeline)

- Model: `sentence-transformers/all-MiniLM-L6-v2`
- Used for: heading classification only (not for chatbot retrieval)
- Seed phrases tuned to bare-word headings (not full sentences)
- Threshold: 0.5 global, 0.45 override for `benefits` and `objectives` categories only
- Confident classification rate: 93% on 5-PDF test set

---

## Recently Completed Work

- Scheduled sync pipeline (`chatbot/backend/sync/`) — uses `requests` + BeautifulSoup (no Playwright)
- Playwright scraper: planned, not implemented
- Feedback system (thumbs up/down stored in the MongoDB `feedback` collection)
- Data freshness indicators in the chat UI
- Sync status header badge (green/amber/grey)
- Hindi and Tamil native-script intent classification (keyword matching before translation fallback)
- Frontend widget with 3 sample messages on the hero page
- FAQ section (9 cards, EN/HI/TA) wired to the widget
- Rotating placeholder text in InputBar
- Generator grounding check (prevents the LLM answering from memory): declines any answer that names none of the retrieved schemes, at any confidence (2026-10-13)
- Scheme-name cleanup: UI-text suffixes stripped from 22 `scheme_name` values in MongoDB and ChromaDB (`chatbot/backend/database/fix_scheme_names.py`, `scheme_name_utils.py`; `load_mongo.py` applies the same cleaning on load)
- WebSocket fix: `/ws/chat` now runs `_process_message` via `run_in_threadpool` with a per-session `asyncio.Lock`, so a slow query no longer blocks other clients or `/health`
- Translation: `myscheme.gov.in` is kept out of translation so translated decline messages keep a correct URL
- Groq fallback chain: `GROQ_MODEL` (`openai/gpt-oss-20b`) -> `GROQ_FALLBACK_MODEL` (`openai/gpt-oss-120b`) on 429 -> backoff -> Ollama; retrieval `top_k=4`
- Eligibility float error fix
- Tamil translation via Helsinki-NLP `opus-mt-dra-en` / `opus-mt-en-dra` (offline, no MSVC needed): en→ta output and ta→en retrieval; fallback chain Helsinki → Google → argostranslate → original query
- Scheme names preserved in English in Tamil responses, with numbered-list and markdown preservation
- `eval_rag.py` `--ids` and `--pause` flags (`--pause` default 3s between LLM calls)
- Eligibility slot capture fix (2026-10-21): session `last_slot_asked` + `eligibility/slot_parser.py` interpret bare replies ("general", "30", "1.2 lakhs"); one re-ask with an example, then a skip offer, then auto-skip on the 3rd failure; "skip" accepted any time. Stray `*` stripped from translated answers. `eval_eligibility` still 95%.
- Frontend redesign committed and pushed (9b66d37)
- Eligibility lookup fix (2026-10-21): session `eligibility_query` holds the original question and drives the final search; topic swaps ("actually, for education") replace it, slot answers never do; no-topic questions search by profile (category/state) and say so. Top-3 retrieval can still include one weak hit.
- Follow-up routing and language fixes (2026-10-27, commit 406e727): router patterns for "tell me more / details of / who can apply / how to apply / documents needed" (en/hi/ta); a message naming a known scheme (`router/scheme_names.py`, normalised like the citation guard, names made only of generic words excluded) goes to scheme search; session memory of the last 5 cited schemes (`session["last_schemes"]`, `router/followup.py`) so "who can apply for it?" / "the first one" retrieve by id (`retriever.fetch_by_ids`); language rule in `translator.resolve_language` (typed text of 3+ words at >= 0.9 detection confidence is answered in its own language, short text and button clicks use the pill; the frontend sends an optional `source`: "typed" | "button"); the translator now sends one sentence per model call so no sentence is dropped. Tests: `chatbot/evaluation/test_followup_regression.py` (8).
- Gemini understanding layer (2026-10-27, `chatbot/backend/nlu/`): see "Gemini understanding layer" below.

---

## Gemini understanding layer

`chatbot/backend/nlu/llm_understander.py` (+ `templates.py`). Called ONLY when the deterministic router returns `out_of_scope` by default (its only low-confidence result), no eligibility slot question is pending, and the follow-up code did not resolve the message. Messages the router already handles never reach it.

- Input sent to Gemini: the message, up to 6 recent chat messages (3 exchanges, 300 chars each), the last scheme names. Aadhaar-style numbers, PAN-style ids, any run of 9+ digits and emails are masked first. Uploaded-document text never goes through this path. Message text and the key are never logged (only call counts and the intent).
- Output: strict JSON validated with Pydantic (`Understanding`: intent, rewritten_query_en, scheme_name, profile_slots, clarifying_question, language). Extra fields, unknown intents and out-of-range slots are rejected. The API schema is sent without `additionalProperties` (the API rejects it); the reply is still validated strictly.
- Use of the result: `rewritten_query_en` is used only for scheme_search / scheme_detail / eligibility, capped at 300 chars and dropped if it looks like instructions. smalltalk / clarify-fallback / unknown-scheme replies are fixed templates (en/hi/ta); out_of_scope gets the existing refusal; clarify shows the model's (filtered, translated) question and the turn stays in the session history so the next reply continues. Stated profile slots plus a qualify/apply question run the eligibility engine whatever intent came back. `scheme_name` is matched with `scheme_names.lookup_scheme_name` and fetched by id; if it is not in the data the bot says so and lists the 3 closest names (it never shows an unrelated scheme as the one asked for). The LLM never writes scheme facts: answers still come from retrieval, generation and the citation guard.
- **Live Gemini tests are PENDING.** On 2026-10-27 the free-tier API returned 503/504 for most calls on both Flash-Lite models for over an hour, so the 30-message live run, the live end-to-end test, the latency/tail measurement and the "minimal thinking helps?" comparison could not be judged. Run them when Gemini is back: `PYTHONPATH=. python -m chatbot.evaluation.test_nlu_layer` (from the repo root; the two `test_live_*` tests print `PENDING` instead of failing while the service is down). Then re-run `python -m chatbot.evaluation.eval_rag` to see how many of the 50 queries reached the LLM and whether out-of-scope is still 10/10.
- Model order: `GEMINI_MODEL_ORDER` (comma-separated) if set, else `GEMINI_MODEL`, `GEMINI_MODEL_FALLBACK`, `GEMINI_MODEL_EXTRA` (default `gemini-3.5-flash`, non-lite, last resort); only after a 404 does it list models and add the oldest `*flash-lite*` text model. A 429/5xx moves on to the next model immediately.
- Circuit breaker: 3 consecutive failures (429/5xx/timeout) switch Gemini off for 60 s (`BREAKER_THRESHOLD`, `BREAKER_COOLDOWN_S`); skipped messages go straight to the old refusal with no wait. Automatic function calling is disabled.
- Typo tolerance without the LLM (`router/typos.py`): "tamilnadu" -> "Tamil Nadu" (all multi-word states) and fuzzy matching of ~40 scheme keywords ("shcemes", "elegible", "requierd"), same first letter, 4+ letters, Latin text only; applied to the English classification and retrieval query. Tests: `test_typo_*` in `test_nlu_layer.py` (10 typo messages: 1/10 routed before, 10/10 after; 5 off-topic typo messages stay out of scope).
- Model (earlier notes): `gemini-2.5-flash-lite` is no longer offered for this key (404). `gemini-2.5-flash-lite` returns 404 for this key (no longer offered to new users); `gemini-3.1-flash-lite` and `gemini-3.5-flash-lite` work. Temperature 0, JSON mode, minimal thinking (`MINIMAL_THINKING`).
- Timeouts: the API rejects deadlines under 10 s, so the SDK deadline is 10 s and a client-side cutoff of 8 s applies. One retry on 429 / 5xx / invalid JSON; a timeout is not retried.
- Fallback: no key, cap reached, 404 on every model, 429/503/504 after the retry, timeout, invalid JSON or any exception -> `understand()` returns None and the chat gives today's out-of-scope refusal. It never raises.
- Caps: `GEMINI_SESSION_CAP` (default 20 API requests per session) and `GEMINI_DAILY_CAP` (default 200 per process per day, a placeholder: set it to about 80% of the real daily limit shown in AI Studio). Both count every request, retries included. The daily counter is in memory and resets on restart.
- Landing page trust copy states that unclear questions go to an external AI service and that uploaded documents do not.
- Tests: `chatbot/evaluation/test_nlu_layer.py` (23 offline tests with a faked model call covering 503, 429, timeout, invalid JSON, schema violations, 404, missing key, caps, privacy, injection and every intent route; 2 live tests that need the key).

---

## Chatbot Evaluation Results

Evaluation harness: `chatbot/evaluation/`. Full detail in `EVAL_REPORT.md`. Latest run: **2026-10-21, full 2,066-scheme corpus** (run from repo root with `python -m chatbot.evaluation.eval_rag` — running from another directory creates an empty ChromaDB and silently breaks retrieval).

Six result columns (per-change effects and the open items in `EVAL_REPORT.md`):

| Metric | 1. 488 schemes (10-10) | 2. 2,066, before token budget | 3. + token budget (14-id subset) | 4. + cleanup: regression | 5. + skip empty description chunks | 6. + guard fix + tighter Hindi patterns (current) | 7. + exact-name prompt line + 2,500-character cap |
|---|---|---|---|---|---|---|---|
| Eligibility accuracy | 95% | 95% | n/a | 95% | 95% | **95% (19/20)** | **95% (19/20)** |
| Out-of-scope declined | 80% (8/10) | 100%, 2 by request failure | 10/10 | 10/10 (8 router, 2 guard) | 10/10 (8 router, 2 guard) | **10/10 (8 router, 2 citation guard)** | **10/10: 8 router, 2 citation guard (35, 38)** |
| Source citation rate | 30% | 26% | 14.3% of 14 ids | 16% | 26% | **28% (14/50)** | **32% (16/50)** |
| Retrieval spot-check (top 5) | 70% | 70% | not run | 60% | 70% | **70% (7/10)** | **70% (7/10)** |
| Average response time | 28.9s | 11.2s | 1.7s | 2.1s | 2.5s | **3.7s** | **4.4s** (2.3s without q29, which took 110s on the Ollama fallback) |
| Groq 413 failures | n/a | 5 | 0 | 0 | 0 | **0** | **0** |
| Answers per model | 20b + Ollama | 20b 9, 120b 6, Ollama 4 | 20b only | 20b 16, 120b 7, Ollama 0 | 20b 19, 120b 4, Ollama 0 | **20b 21, 120b 3, Ollama 0** | **20b 13, 120b 10, Ollama 1** |
| Mongo docs / Chroma chunks | 488 / 1,952 | 2,066 / 8,264 | 2,066 / 8,264 | 2,066 / 8,264 | 2,066 / 7,528 | **2,066 / 7,528** | **2,066 / 7,528** |

Column 7 (kept, committed): one added line in the generator's system prompt ("Cite each scheme using its exact name as written in the context.") and `SCHEME_CHAR_CAP` raised from 1,500 to 2,500 characters (5,500-token prompt cap and 413 retry unchanged). Raw results: `eval_rag_results.json` (column 7), `eval_rag_results_before_experiment.json` (column 6). Largest request 4,093 Groq prompt tokens (was about 1,800), so there were more 429s (24 rate-limit events against 3), and one query (q29, "What identity proof documents ...") fell to Ollama and took 110s. Per-query: q3, q22 and q24 are now answered (4 sources each), q4 and q28 are still declined at low confidence (the model itself says "no reliable information"), q44 flipped from answered to declined (typo query, wording variance). Scheme/benefit queries still without sources: q4, q5, q9 (correct, not in the dataset), q26, q28. Paris: `names_scheme("The capital of France is Paris.", ...)` is False for "Atal Pension Yojana", "Dr. B." and "E."; q35 is declined by the citation guard with 0 sources.

Column 6 = token budget (per-scheme 1,500-character cap, 5,500-token prompt cap, 4 -> 3 -> 2 scheme retry on 413) + pop-up text stripped from all descriptions + 73 file-name scheme names recovered + content-free description chunks removed from Chroma + citation guard that normalises names (edge punctuation, Unicode hyphens/quotes, min 4 characters; `test_citation_guard.py`) + Romanized-Hindi `kya hai` / `batao` / `bataiye` / `ke baare mein` only with a scheme word. Differences of a query or two between runs are model wording variance.

**Chroma now holds 7,528 chunks** (8,264 before); every scheme still has at least 3 (736 schemes have 3, 1,330 have 4).

**What went wrong in column 4:** the cleanup left 732 empty descriptions, whose name-only chunks outranked real matches (q1: the real Atal Pension Yojana chunk was at rank #22). Skipping them in `load_chroma.py` / `fix_descriptions.py` restored the numbers.

**Caveat on the 100% decline rate in column 2:** q35 and q38 were declined only because Groq returned 413 and every fallback failed. From column 3 on, both are declined by the citation guard itself.

---


## Known Limitations

- **Tamil translation quality:** Helsinki `opus-mt-en-dra` output is readable but often garbled for descriptive text (repetition, lost figures, mangled place names). NLLB-200 or IndicTrans2 would be a quality upgrade, not a blocker.
- **Tamil specific scheme-name retrieval:** fails for Tamil-script scheme names (eval ids 5, 6, 18, 26) because multilingual-e5-small does not embed them accurately; broad category queries (farmers, women's schemes) work. Queries are now translated ta→en with Helsinki before retrieval, but it garbles proper nouns (e.g. "Airavata", "Amma Two Wheeler"), so these queries are expected to still miss; not re-evaluated since the change.
- **MyScheme sync:** `scheme_sync.py` currently uses `requests` + BeautifulSoup only; a Playwright scraper is planned but not implemented. Needs API key registration, or a Playwright scraper (not yet built), to fetch JS-rendered pages.
- **Groq rate limits:** the free tier allows 8,000 tokens/min per model (1,000 requests/day); a RAG request uses ~4-5k tokens. The 20b -> 120b fallback doubles the budget, but bursts of 3+ heavy queries in a minute still exhaust both buckets and fall to Ollama. Ollama's fallback model is `OLLAMA_MODEL=gemma3:4b` (installed), but its 120s timeout makes that path slow under load.
- Eligibility engine evaluates merged multi-clause condition strings as one unit (Airavata Scheme case fails).
- **Prompt size vs Groq free tier:** handled by a per-scheme 1,500-character cap, a ~5,500-token prompt cap and a 4 -> 3 -> 2 scheme retry on 413 (`rag/generator.py`).
- **13 schemes still have truncated scheme names** (`Dr. B.`, `E.`, `'`, `H.`, `J.`, `Meit`, `MMKY-`, ...), recoverable from the source PDFs like the 73 file-name ones were.
- **732 schemes have an empty description** after the pop-up cleanup (the extraction only captured a header) and 4 more are under 40 characters; they have no description chunk in Chroma (deliberately), only benefits/eligibility/application. 67 other-section chunks are also content-free.
- **The citation guard's exact-name match is brittle against model abbreviations** ("Amma Two Wheeler Scheme" for "... for Working Women", "Assam Arogya Nidhi (AAN) Scheme"): q3 and q24 decline at high confidence in some runs. The trailing-punctuation case (`Abhayakiranam Scheme-`) is fixed.
- **The per-scheme cap is now 2,500 characters (was 1,500).** Longer schemes are still truncated; raising it further risks the 5,500-token budget and more Groq 429s (24 rate-limit events in the column 7 run against 3). Partly mitigated, not solved: q4, q5, q26 and q28 are still open.
- q6 (Tamil) now answers about a wrong scheme (Snehayanam) with sources; Tamil specific-scheme retrieval is still open.
- The pop-up sentence also remains inside 84 `application`/`eligibility`/`benefits` chunks.

---

## Remaining Work (in order)

Done: extraction 2,066/2,066, MongoDB + ChromaDB re-ingest, token budget with 413 retry, pop-up text stripped from all descriptions (`fix_descriptions.py`), 73 file-name scheme names recovered from the source PDFs (`fix_filename_schemes.py`), content-free description chunks skipped, citation-guard name normalisation (trailing punctuation, Unicode hyphens, min 4 characters), Romanized-Hindi router patterns tightened to require a scheme word, full re-evaluation.

1. Make the citation guard tolerate model abbreviations of scheme names (leading words / token overlap), and consider raising the per-scheme cap from 1,500 to about 3,000 characters; re-run the eval
2. Recover the 13 remaining truncated scheme names the same way as the 73; consider the 67 content-free benefits/eligibility/application chunks and the pop-up text left in 84 chunks
3. Tamil retrieval for queries that name a specific scheme (q5, q6, q18, q26 still miss; q6 now answers with a wrong scheme)
4. MyScheme API key, or build the (planned, not yet implemented) Playwright scraper, for the sync pipeline
5. Feedback buttons in the hero widget

### To Resume in a New Claude Session
Paste this at the start:
```
I'm continuing an existing project. Read these files before doing anything:
- PROJECT_PLAN.md
- PROJECT_HANDOFF.md
- RESUME_LATER.md

Confirm branch:
  git rev-parse --show-toplevel
  git branch --show-current
Expected: C:/Faizal/Government_Scheme-AI, main

Then tell me what you want to do next.
```

---

## Tech Stack — Chatbot

| Component | Decision |
|---|---|
| Database | MongoDB Atlas free tier |
| Vector Store | ChromaDB persistent local (`chatbot/data/chroma_db/`) |
| Embeddings | `intfloat/multilingual-e5-small` (handles Tamil/Hindi/English natively) |
| Retrieval | Hybrid — MongoDB metadata filter + ChromaDB semantic search |
| LLM Primary | Groq, model via `GROQ_MODEL` env var |
| LLM Fallback | Groq gpt-oss-120b on 429, then Ollama `gemma3:4b` (the installed model), controlled fallback only |
| LLM Architecture | Factory pattern (`llm/factory.py`) |
| Embedding Architecture | Abstraction layer (`embeddings/base.py`) |
| OCR | PyMuPDF (text PDFs) + PaddleOCR (scanned fallback) |
| Document Extraction | Instructor + Pydantic + Groq |
| Backend | FastAPI + WebSocket |
| Query Router | Deterministic Python (5 intents) |
| Translation | `langdetect` for detection; Helsinki-NLP Marian models for Tamil, argostranslate for Hindi |
| Frontend | React + Tailwind CSS |
| Evaluation | 50 curated test queries, Ragas metrics |

---

## Environment Variables Required

```
MONGODB_URI=
GROQ_API_KEY=
GROQ_MODEL=
OLLAMA_MODEL=gemma3:4b
CHROMA_PERSIST_PATH=chatbot/data/chroma_db
UNSTRUCTURED_API_KEY=       ← already set, used by extraction pipeline
GEMINI_API_KEY=             ← chatbot/.env only; blank disables the understanding layer
GEMINI_MODEL=gemini-3.1-flash-lite
GEMINI_MODEL_FALLBACK=gemini-3.5-flash-lite
GEMINI_SESSION_CAP=20       ← optional, API requests per session
GEMINI_DAILY_CAP=200        ← optional, set to ~80% of the daily limit in AI Studio (the real limit has not been read yet)
GEMINI_MODEL_EXTRA=gemini-3.5-flash   ← optional non-lite last resort
GEMINI_MODEL_ORDER=         ← optional comma-separated override of the whole order
```

`.env` must be in `.gitignore` — never commit API keys.

---

## requirements.txt Location

`requirements.txt` lives at `backend/requirements.txt` — not at the repo root. New chatbot dependencies must be appended to this file only, never overwritten, and no new requirements.txt should be created elsewhere.