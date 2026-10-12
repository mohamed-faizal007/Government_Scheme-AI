# Government Scheme AI — Project Handoff Document

Last updated: October 2026
Status: Extraction in progress (488/2066 PDFs processed). Chatbot built (backend, frontend, sync pipeline, evaluation).

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
- Processed: 488 (in `dataset/gov_myscheme/test_output_unstructured/`)
- Remaining: 1,578
- To continue: run `python backend/extraction/batch_run_200.py` (processes next 200)
- Resume is safe at any time — idempotent, never reprocesses completed files

### Git
- Active branch: `main`
- Last commit: `35fa68a` — Tamil translation: Helsinki-NLP offline model, scheme name protection, numbered list preservation

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

- Scheduled sync pipeline (`chatbot/backend/sync/`)
- Playwright-based scraper for the sync pipeline
- Feedback system (thumbs up/down stored in the MongoDB `feedback` collection)
- Data freshness indicators in the chat UI
- Sync status header badge (green/amber/grey)
- Hindi and Tamil native-script intent classification (keyword matching before translation fallback)
- Frontend widget with 3 sample messages on the hero page
- FAQ section (9 cards, EN/HI/TA) wired to the widget
- Rotating placeholder text in InputBar
- Generator grounding check (prevents the LLM answering from memory)
- Eligibility float error fix
- Tamil translation via Helsinki-NLP `opus-mt-dra-en` / `opus-mt-en-dra` (offline, no MSVC needed): en→ta output and ta→en retrieval; fallback chain Helsinki → Google → argostranslate → original query
- Scheme names preserved in English in Tamil responses, with numbered-list and markdown preservation
- `eval_rag.py` `--ids` and `--pause` flags (`--pause` default 3s between LLM calls)

---

## Chatbot Evaluation Results

Evaluation harness: `chatbot/evaluation/`. Full detail in `EVAL_REPORT.md`. Latest run: 2026-10-10 (run from repo root with `python -m chatbot.evaluation.eval_rag` — running from another directory creates an empty ChromaDB and silently breaks retrieval).

| Metric | Result |
|---|---|
| Eligibility accuracy | 95% (19/20) |
| Source citation rate | 30% (15/50) |
| Out-of-scope decline rate | 80% (8/10) |
| Retrieval spot-check (top 5) | 70% (7/10) |
| Average response time | 28.9s (Groq 429 retries + Ollama fallback) |

**Note:** out-of-scope decline was 100% in the earlier run; the latest run shows 80% because two queries (e.g. "What is the capital of France?") were answered from LLM memory. A generator grounding check has since been added; re-run the eval to confirm it closes the leak.

---

## Known Limitations

- **Tamil translation quality:** Helsinki `opus-mt-en-dra` output is readable but often garbled for descriptive text (repetition, lost figures, mangled place names). NLLB-200 or IndicTrans2 would be a quality upgrade, not a blocker.
- **Tamil specific scheme-name retrieval:** fails for Tamil-script scheme names (eval ids 5, 6, 18, 26) because multilingual-e5-small does not embed them accurately; broad category queries (farmers, women's schemes) work. Queries are now translated ta→en with Helsinki before retrieval, but it garbles proper nouns (e.g. "Airavata", "Amma Two Wheeler"), so these queries are expected to still miss; not re-evaluated since the change.
- **MyScheme sync:** needs API key registration OR Google unblock for the Playwright scraper.
- **Groq rate limits:** the free tier causes fallback to Ollama on heavy eval runs (11 queries in the latest run), inflating response time and mixing models in eval answers.
- Eligibility engine evaluates merged multi-clause condition strings as one unit (Airavata Scheme case fails).
- Only 488 of 2,066 schemes are loaded; schemes outside this set (e.g. PM-Kisan) cannot be found.

---

## Remaining Work (in order)

1. Process remaining 1,578 PDFs (`python backend/extraction/batch_run_200.py`, 200 per batch, ~70 min each, idempotent)
2. Re-ingest the full dataset into MongoDB + ChromaDB
3. Final evaluation on the complete dataset
4. MyScheme API key, or unblock Google, for the sync pipeline

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
| LLM Fallback | Ollama + Qwen2.5:3B, controlled fallback only |
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
OLLAMA_MODEL=qwen2.5:3b
CHROMA_PERSIST_PATH=chatbot/data/chroma_db
UNSTRUCTURED_API_KEY=       ← already set, used by extraction pipeline
```

`.env` must be in `.gitignore` — never commit API keys.

---

## requirements.txt Location

`requirements.txt` lives at `backend/requirements.txt` — not at the repo root. New chatbot dependencies must be appended to this file only, never overwritten, and no new requirements.txt should be created elsewhere.