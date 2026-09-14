## 1. Complete PDF Processing (Priority: High)

393 of 2,066 PDFs have been processed. 1,673 remain.

To continue, open a new Claude session in VS Code and paste:

    I'm continuing an existing project. Read these two files before doing anything:
    - PROJECT_PLAN.md (repo root)
    - PROJECT_HANDOFF.md (repo root)

    Once you've read both, confirm you're on the right branch:
      git rev-parse --show-toplevel
      git branch --show-current
    Expected: C:/Faizal/Government_Scheme-AI, branch feature/unstructured-extraction

    Then run the next 200 unprocessed PDFs using batch_run_200.py and show me the summary when done.

Repeat "Continue next 200" until all 2,066 are done.
batch_run_200.py is idempotent — safe to stop and resume anytime.
Output folder: test_output_unstructured/

---

## 2. Merge to Main (Priority: High — do after all 2,066 are processed)

Branch feature/unstructured-extraction has never been merged to main.
All pipeline work lives on this branch.

Steps:
- Confirm all 2,066 JSONs are in test_output_unstructured/
- Run a final schema validation pass across all files
- Merge feature/unstructured-extraction into main via PR

---

## 3. Known Bugs — Not Fixed (Lower Priority — assess after full dataset is done)

These are documented, understood, and will not block the chatbot:

| Bug | Frequency | Impact |
|---|---|---|
| FAQ content misclassified into benefits | ~64% of files | Low for RAG — content is present, wrong field |
| scheme_name corrupted with UI text ("Are you sure you want to sign out?") | ~5% of files | Medium — scheme name is wrong |
| objectives empty (no heading in source PDF) | ~80% of files | Low — content is in overview.description instead |
| a-gainer pattern: objective text in benefits | ~9% of files | Low for RAG |
| \ufeff invisible character escaping label filter | ~1% of files | Very low |
| Glued preamble fragments in eligibility (5-word+ Title Case labels) | Small % | Low |

---

## 4. Database + Embeddings + Chatbot (Priority: High — can start now on 393 JSONs)

This is the next active work. Steps in order:

### Step 1 — Load JSONs into MongoDB
- Use MongoDB Atlas free tier (cloud) or local MongoDB
- One document per JSON file
- Index on scheme_name

### Step 2 — Generate Embeddings
- Model: sentence-transformers/all-MiniLM-L6-v2 (already installed in venv)
- Embed each scheme's key fields: scheme_name + description + benefits + eligibility
- Store embeddings alongside documents

### Step 3 — Vector Store
- Use FAISS or ChromaDB (both free, local)
- Store embeddings for semantic search

### Step 4 — RAG Layer
- User query → embed query → semantic search → retrieve top-K schemes → pass to LLM
- LLM options (free): Groq (fast, free tier), Ollama/Qwen (local, no quota)

### Step 5 — Chatbot Interface
- Simple interface options: Streamlit (easiest, free) or FastAPI + basic HTML

---

## 5. Unstructured API Page Usage

page_usage.log is in dataset/gov_myscheme/logs/
Free tier limit: 15,000 pages/month
Check this before each batch run to avoid hitting the cap unexpectedly.

---

## Current State Summary

| Item | Status |
|---|---|
| PDFs processed | 393 / 2,066 |
| Active branch | feature/unstructured-extraction |
| Pipeline files | batch_run_200.py, batch_extract_unstructured.py |
| Output folder | test_output_unstructured/ |
| json_output/ | Untouched (original Gemini outputs) |
| batch_extract.py | Untouched (original Gemini pipeline) |
| postprocess_faq.py | Written but not being used — drop it |


so is this data enough for me to later continue with the work which im skipping rn


Yes, completely. Here's why:

What you're skipping: Processing the remaining 1,673 PDFs.

What you have now: 393 fully validated, schema-passing JSONs — enough to build, test, and demo a working chatbot end-to-end.

When you come back to it: You run batches of 200, drop the new JSONs into the same output folder, and re-run the MongoDB ingestion script to pick them up. The chatbot doesn't need to be rebuilt — just the data layer gets updated. One re-run command.

Nothing you build now will need to be redone later. The database schema, embedding model, RAG logic, and chatbot interface will all work identically whether you have 393 or 2,066 schemes loaded. Adding more schemes later is purely additive.

So yes — move forward now. The 393 files are real data, good enough to build on. Want the prompt to start the MongoDB + embeddings step?

