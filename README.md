# SchemeBot — Government Scheme AI

SchemeBot is a multilingual (English, Hindi, Tamil) chatbot that answers questions about Indian government schemes using the 2,066 scheme records scraped from myScheme. It routes each message by intent, retrieves matching schemes from ChromaDB, and has an LLM write an answer grounded only in the retrieved text, with a citation guard that declines answers which name no retrieved scheme. It also runs a rule-based eligibility check (asking for age, state, income, category and gender, or reading them from an uploaded PDF certificate) and verifies uploaded documents.

This branch (`review3-submission`) is the chatbot as described in the Review III report (commit `0a51230`).

## Pipeline

Intent router → ChromaDB retrieval (`multilingual-e5-small`, fetches 2×k, groups by scheme, k=4, 2,500-char cap per scheme) → Groq `gpt-oss-20b`, then `gpt-oss-120b` on a 429, then local Ollama → citation guard → Hindi/Tamil translation with protected scheme names. FastAPI serves a WebSocket (`/ws/chat`) with each message handled in a thread pool; a React (Vite) frontend sits on top.

## Requirements

- Python 3.13 (the version the project venv was built and tested with)
- Node.js 20+ and npm (tested with Node 20.20.2, npm 10.8.2)
- A MongoDB Atlas cluster (database `gov_scheme_ai`, collection `schemes`)
- A Groq API key
- Ollama with `gemma3:4b` pulled (optional, only used when both Groq models are rate-limited)

## Setup

Run from the repo root.

```powershell
git clone https://github.com/mohamed-faizal007/Government_Scheme-AI.git
cd Government_Scheme-AI
git switch review3-submission

python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r chatbot/requirements.txt

copy chatbot\.env.example chatbot\.env
# edit chatbot\.env: set MONGODB_URI and GROQ_API_KEY
```

`chatbot/requirements.txt` was built from the imports in `chatbot/backend` and pinned to the versions installed in the project venv when it was written. It has not been tested on a clean install. The OCR fallback for scanned PDFs (`paddleocr`, `pdf2image`) is listed as optional and commented out; digital PDFs work without it.

`OLLAMA_MODEL` in `.env.example` is `gemma3:4b` (what the report used). The default in `chatbot/backend/config.py` is `qwen2.5:3b`, which is used if the variable is not set.

### Load the data

The scheme JSONs live in `dataset/gov_myscheme/test_output_unstructured/` (2,066 files). Both loaders are idempotent, per their docstrings:

```powershell
python -m chatbot.backend.database.load_mongo
python -m chatbot.backend.database.load_chroma
```

Expected result: 2,066 documents in MongoDB and 7,528 chunks in ChromaDB (8,264 minus 736 content-free description chunks). I did not re-run these loaders while preparing this README, because my databases were already loaded; I only confirmed the counts (2,066 / 7,528) and the `/health` endpoint.

### Frontend

```powershell
cd chatbot/frontend
npm install
```

## Run

Backend (terminal 1, from the repo root, venv active):

```powershell
uvicorn chatbot.backend.api.main:app --port 8000
```

The first start takes a while because the embedding model loads. Check it with `http://localhost:8000/health`, which should report 2,066 schemes and 7,528 embeddings.

Frontend (terminal 2):

```powershell
cd chatbot/frontend
npm run dev
```

Open http://localhost:5173.

## Sample queries

| Try | Expect |
|---|---|
| `What schemes are available for farmers?` | A cited list of schemes |
| `किसानों के लिए कौन सी योजनाएं हैं?` | Hindi answer with the scheme names kept intact |
| `விவசாயிகளுக்கு என்ன திட்டங்கள் உள்ளன?` | Tamil answer |
| `What is the capital of France?` | Declined, points to myscheme.gov.in |
| `Am I eligible for a farming subsidy?` then `I am 45 years old`, `My state is Assam`, `My annual income is 80000`, `I belong to the general category`, `I am male` | Follow-up questions, then eligible / not eligible with reasons and conditions that could not be verified |

For document verification, upload a PDF (an income or caste certificate) in the chat; the extracted fields fill the eligibility profile.

## Folder structure

```
chatbot/
  backend/
    api/          FastAPI app: /ws/chat, /chat, /health, /profile, /document/upload, /feedback, /sync/*
    router/       intent classifier (English/Hindi/Tamil keywords)
    retrieval/    ChromaDB retrieval
    embeddings/   multilingual-e5-small wrapper
    rag/          context building, generation, citation guard
    llm/          Groq, Ollama providers and factory
    eligibility/  slot capture, rules engine, user profile
    documents/    PDF text extraction and field extraction
    translation/  Hindi (Argos) and Tamil (Helsinki-NLP) translation
    database/     MongoDB/ChromaDB loaders and cleanup scripts
    sync/         scheduled scheme sync (not needed to run the chatbot)
    config.py     settings read from chatbot/.env
  evaluation/     evaluation scripts, results and EVAL_REPORT.md
  frontend/       React + Vite UI
  .env.example    variable names the backend reads
  requirements.txt
backend/          PDF extraction pipeline (not part of the chatbot runtime)
dataset/          scheme PDFs and extracted JSON
docs/             project plans and notes
```

## Known limitations

- **Tamil proper nouns:** retrieval for Tamil queries goes through translation, so scheme and place names can be mistranslated or missed.
- **Groq quota:** the free tier allows 8,000 tokens per minute per model. Several heavy queries in a minute exhaust both models and fall back to Ollama, which is slow (120 s timeout).
- **No live data sync:** answers come from the snapshot of 2,066 schemes in MongoDB/ChromaDB. The sync scheduler exists but needs a myScheme API key, and the API returned 401 without one.
- **Age from documents:** uploading a certificate with a date of birth does not compute age; `age` is reported as a failed field and the bot asks for it.
- **Eligibility is rule-based and conservative:** conditions the rules engine cannot parse are listed as unverifiable instead of being scored.
- **Scanned PDFs** need the optional PaddleOCR packages, which were not tested.
- On a very first `/health` call, ChromaDB may log a one-off tenant error if two requests arrive at the same moment; later calls succeed.
