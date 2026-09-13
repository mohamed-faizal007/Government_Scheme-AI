# Government Scheme AI — Project Handoff Document

Last updated: September 2026
Status: Extraction pipeline complete (488/2066 PDFs). Chatbot build starting.

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
feature/unstructured-extraction
```

This branch has NEVER been merged to main. All pipeline work lives here.
Do not merge to main until all 2,066 PDFs are processed and validated.

---

## Current State

### PDF Processing
- Total PDFs: 2,066
- Processed: 488 (in `dataset/gov_myscheme/test_output_unstructured/`)
- Remaining: 1,578
- To continue: run `python backend/extraction/batch_run_200.py` (processes next 200)
- Resume is safe at any time — idempotent, never reprocesses completed files

### Git Log (as of last session)
```
fbf9039  Add Unstructured hi_res + embedding classifier pipeline (5-PDF validation)
         + all bug fixes from this session (committed together)
ecf4266  Merge pull request #1 from mohamed-faizal007/feature/docling-parser
6a05b02  Implement Gemini-based PDF extraction pipeline
ae051e2  Add dataset download, validation, and PDF extraction pipeline
460254e  Initialize project structure
6fe4ee4  Initial commit
```

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

## What to Do Next

### Immediate — Start Chatbot Build
Paste `CHATBOT_IMPLEMENTATION_PROMPT.md` into a new Claude Code session.
Build on the 488 existing JSONs — do not wait for all 2,066.

### Background — Complete PDF Processing
Run `python backend/extraction/batch_run_200.py` in batches of 200.
Each batch takes ~70 minutes. Safe to run overnight.
After all 2,066 done:
1. Re-run MongoDB and ChromaDB ingestion scripts
2. Run final schema validation
3. Merge `feature/unstructured-extraction` into `main` via PR

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
Expected: C:/Faizal/Government_Scheme-AI, feature/unstructured-extraction

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
| Translation | `langdetect` for detection, `googletrans` for output translation |
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