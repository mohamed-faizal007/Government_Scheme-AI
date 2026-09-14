# Chatbot Implementation Prompt — Government Scheme AI

Paste this into a new Claude Code session to build the chatbot phase by phase.

---

## ⚠️ CRITICAL — Read Before Touching Anything

This project has an existing, working extraction pipeline. The chatbot is built ON TOP of it. You must never modify, overwrite, or re-run any part of the extraction pipeline.

### What Already Exists — DO NOT TOUCH

```
backend/                          ← existing extraction pipeline — read only
├── extraction/
│   ├── batch_extract.py          ← original Gemini pipeline — never modify
│   ├── batch_extract_unstructured.py  ← active pipeline — never modify
│   ├── batch_run_200.py          ← batch runner — never modify
│   ├── batch_extract_final.py    ← never modify
│   ├── preprocess.py             ← noise cleaning — never modify
│   ├── postprocess.py            ← post processing — never modify
│   ├── insert_boundaries.py      ← boundary fix — never modify
│   ├── classify_headings.py      ← embedding classifier — never modify
│   ├── extract_sections.py       ← section extractor — never modify
│   ├── parse_unstructured.py     ← Unstructured API parser — never modify
│   ├── schema.py                 ← Pydantic schema — never modify
│   ├── validate_json.py          ← validator — never modify
│   └── postprocess_faq.py        ← written but unused — ignore
│
dataset/
├── gov_myscheme/
│   ├── unique_pdfs/              ← source PDFs — never modify
│   ├── json_output/              ← original Gemini outputs — never modify
│   └── logs/                     ← pipeline logs — never modify
│
dataset/gov_myscheme/test_output_unstructured/  ← 488 validated JSONs — READ ONLY
                                     this is your data source for the chatbot
                                     do not delete, overwrite, or re-extract
```

### What the Extraction Pipeline Already Does (do not redo any of this)

The following has already been built and validated across 488 PDFs:

1. ✅ PDF parsing via Unstructured API (`strategy="hi_res"`)
2. ✅ Section boundary insertion (`insert_boundaries.py`)
3. ✅ Heading classification via `sentence-transformers/all-MiniLM-L6-v2` embedding classifier
4. ✅ Nav-bar false heading suppression (gap=0 chain rule)
5. ✅ Button phrase pre-stripping ("Check Eligibility", "Apply Now")
6. ✅ Orphan pre-heading content captured into `overview.description`
7. ✅ Footer noise stripping (8 known footer strings)
8. ✅ Label artifact filtering from `eligibility.conditions`
9. ✅ Duplicate heading continuation merge
10. ✅ Pydantic schema validation on every output JSON
11. ✅ Resume-safe batch processing (`batch_run_200.py`)

### Known Limitations in Existing Output (accepted, do not try to fix)

These are documented quality issues in `test_output_unstructured/`. They do not block the chatbot:

| Issue | Frequency | Impact on Chatbot |
|---|---|---|
| FAQ content in benefits field | ~64% of files | Low — content is present, wrong bucket, RAG still finds it |
| scheme_name corrupted with UI text | ~5% of files | Medium — handle gracefully in MongoDB load |
| objectives field empty | ~80% of files | Low — content is in `overview.description` instead |
| Objective text in benefits | ~9% of files | Low for RAG |
| Glued preamble fragments in eligibility | Small % | Low |

### Your Data Source for the Chatbot

```
dataset/gov_myscheme/test_output_unstructured/
```

488 JSON files. Each follows this schema (`backend/extraction/schema.py`):

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

The chatbot reads from this folder (`dataset/gov_myscheme/test_output_unstructured/`). It never writes back to it.

### Active Git Branch

```
feature/unstructured-extraction
```

All existing pipeline code lives here. All new chatbot code goes under `chatbot/` on this same branch. Do not create a new branch — do not merge to main until all 2,066 PDFs are processed.

### Remaining PDF Processing (background task)

1,578 PDFs are still unprocessed. This runs in the background independently:
- Command to continue: `python backend/extraction/batch_run_200.py` (processes next 200 unprocessed PDFs)
- Safe to run at any time — idempotent, never reprocesses completed files
- Output goes to `dataset/gov_myscheme/test_output_unstructured/` automatically
- After all 2,066 done: re-run `load_mongo.py` and `load_chroma.py` to pick up new schemes

Do not wait for all 2,066 to finish before building the chatbot. Build on the 488 now.

---

## Project Structure to Create

Create all new chatbot code under a new top-level folder `chatbot/`:

```
chatbot/
├── backend/
│   ├── api/
│   │   ├── main.py
│   │   └── routes/
│   ├── database/
│   │   ├── mongo_client.py
│   │   ├── load_mongo.py
│   │   └── load_chroma.py
│   ├── embeddings/
│   │   ├── base.py
│   │   └── multilingual_e5.py
│   ├── llm/
│   │   ├── base.py
│   │   ├── groq_provider.py
│   │   ├── ollama_provider.py
│   │   └── factory.py
│   ├── retrieval/
│   │   └── retriever.py
│   ├── rag/
│   │   ├── generator.py
│   │   └── rag_chain.py
│   ├── router/
│   │   └── intent_classifier.py
│   ├── eligibility/
│   │   ├── user_profile.py
│   │   ├── rules_engine.py
│   │   └── slot_filler.py
│   ├── documents/
│   │   ├── ocr.py
│   │   └── extractor.py
│   ├── translation/
│   │   └── translator.py
│   └── config.py
├── frontend/
│   (React app — created in Phase 6)
├── evaluation/
│   ├── test_queries.json
│   ├── eval_rag.py
│   └── eval_eligibility.py
├── data/
│   └── chroma_db/
└── .env
```

---

## Ground Rules — Apply to Every Phase

- Never modify existing extraction pipeline files
- Never hardcode API keys — always use `.env`
- Stop after each phase and show me test results before proceeding
- Git commit after each phase with a clear message
- Create new files for new functionality — never overwrite working files
- Every phase must include a working test before moving on

---

## PHASE 1 — Project Setup and Configuration

### 1.1 Environment
Create `chatbot/.env` with these keys (leave values blank — I will fill them):
```
MONGODB_URI=
GROQ_API_KEY=
GROQ_MODEL=
OLLAMA_MODEL=qwen2.5:3b
CHROMA_PERSIST_PATH=chatbot/data/chroma_db
```

Create `chatbot/backend/config.py`:
- Load all env vars using `python-dotenv`
- Expose as a `Settings` Pydantic model
- Single import for all config across the project

### 1.2 Install Dependencies
Add to the existing `backend/requirements.txt` — append only, do not overwrite, do not create a new requirements.txt elsewhere:
```
pymongo
chromadb
sentence-transformers
langdetect
groq
instructor
paddleocr
pdf2image
Pillow
fastapi
uvicorn
websockets
python-dotenv
ragas
```

### 1.3 LLM Abstraction
Create:
- `chatbot/backend/llm/base.py` — abstract base class `BaseLLM` with method `generate(prompt: str, system: str) -> str`
- `chatbot/backend/llm/groq_provider.py` — implements `BaseLLM` using Groq API, model from `GROQ_MODEL` env var
- `chatbot/backend/llm/ollama_provider.py` — implements `BaseLLM` using Ollama local API at `http://localhost:11434`, model from `OLLAMA_MODEL` env var
- `chatbot/backend/llm/factory.py` — `get_llm(provider: str = "groq") -> BaseLLM`

Groq failure handling — distinguish these cases explicitly:
- Rate limit (429) → retry with exponential backoff, max 3 retries
- Temporary failure (503) → retry once
- Invalid response → log and fall back to Ollama
- Network failure → log and fall back to Ollama
- Log which provider was used for every single response
- Do NOT automatically fall back to Ollama for rate limits — retry Groq first

### 1.4 Embedding Abstraction
Create:
- `chatbot/backend/embeddings/base.py` — abstract base class `BaseEmbedder` with method `embed(texts: list[str]) -> list[list[float]]`
- `chatbot/backend/embeddings/multilingual_e5.py` — implements `BaseEmbedder` using `intfloat/multilingual-e5-small`
  - IMPORTANT: this model requires texts to be prefixed
  - Queries use `"query: "` prefix
  - Documents use `"passage: "` prefix
  - Implement this correctly — wrong prefix degrades retrieval quality significantly

Test Phase 1 by:
- Importing `get_llm()` and calling it with a simple prompt, print the response and which provider was used
- Embedding 3 test strings and printing their shapes

Stop and show me results before Phase 2.

---

## PHASE 2 — Data Layer (MongoDB + ChromaDB)

### 2.1 MongoDB
Create `chatbot/backend/database/mongo_client.py`:
- Single `MongoClient` instance using `MONGODB_URI` from config
- Database: `gov_scheme_ai`
- Collection: `schemes`

Create `chatbot/backend/database/load_mongo.py`:
- Read all JSONs from `dataset/gov_myscheme/test_output_unstructured/` — this folder is read-only, do not modify it
- For each JSON, create a MongoDB document with ALL original fields plus:
  - `source_file`: original filename
  - `ingested_at`: timestamp
  - `embedding_status`: `"pending"`
- Idempotent — match on `source_file`, skip if already exists, never duplicate
- Handle the known ~5% scheme_name corruption gracefully: if `scheme_name` contains `"Are you sure you want to sign out?"` or similar UI text, log a warning but still ingest the document — do not skip it
- Create indexes on: `scheme_name`, `source_file`
- Print summary: inserted / skipped / failed

### 2.2 ChromaDB
Create `chatbot/backend/database/load_chroma.py`:
- Use ChromaDB persistent client at `CHROMA_PERSIST_PATH` from config — never in-memory
- Collection name: `schemes`
- For each scheme in MongoDB, create chunks — one chunk per section:
  - `description` chunk: `"passage: {scheme_name}. {overview.description}"`
  - `benefits` chunk: `"passage: {scheme_name} benefits: {benefits.other_benefits joined with space}"`
  - Note: benefits may contain FAQ content due to a known extraction limitation — this is acceptable, the content is still retrievable
  - `eligibility` chunk: `"passage: {scheme_name} eligibility: {eligibility.conditions joined with space}"`
  - `application` chunk: `"passage: {scheme_name} application: {application.steps joined with space}"`
- Each chunk stored with metadata:
```json
  {
    "scheme_id": "mongodb _id as string",
    "scheme_name": "...",
    "source_file": "...",
    "section": "description|benefits|eligibility|application",
    "state": "extracted from eligibility text if present, else empty string",
    "chunk_id": "source_file_section"
  }
```
- Embed using `multilingual-e5-small` with `"passage: "` prefix
- Idempotent — skip chunk_ids already in ChromaDB
- Update `embedding_status` to `"done"` in MongoDB after embedding
- Print summary: embedded / skipped / failed

### 2.3 Verification
Run both scripts and verify:
- MongoDB document count matches JSON file count in `dataset/gov_myscheme/test_output_unstructured/`
- ChromaDB chunk count = MongoDB count × 4
- Test query: embed `"query: housing subsidy for poor families"` → search ChromaDB → print top 3 scheme names and sections returned

Stop and show me verification results before Phase 3.

---

## PHASE 3 — Retrieval Layer

Create `chatbot/backend/retrieval/retriever.py`:

### Hybrid Retrieval
Function: `retrieve(query: str, filters: dict = None, top_k: int = 5) -> list[dict]`

Step 1 — Extract structured filters from query using regex:
- State names (Tamil Nadu, Maharashtra, Delhi, etc.) → `filter["state"]`
- Category keywords (SC, ST, OBC, general, women, farmer, student, differently abled) → `filter["category"]`
- Benefit type (housing, education, health, agriculture, employment) → `filter["benefit_type"]`

Step 2 — ChromaDB semantic search:
- Embed query with `"query: "` prefix using `multilingual-e5-small`
- Search ChromaDB with extracted metadata filters where available
- Retrieve top `top_k * 2` candidates (over-fetch for reranking)

Step 3 — Fetch full documents from MongoDB:
- Use `scheme_id` from ChromaDB metadata to fetch full scheme documents
- Deduplicate by `scheme_id` (multiple chunks from same scheme may match)

Step 4 — Return top `top_k` unique schemes with:
- Full scheme document
- Which section matched (`section` from chunk metadata)
- Similarity score

Test with 5 queries:
1. `"schemes for farmers in Tamil Nadu"` (English with state filter)
2. `"housing subsidy for SC category"` (English with category filter)
3. `"education scholarship below 2 lakh income"` (English with benefit type)
4. `"விவசாயிகளுக்கான திட்டங்கள்"` (Tamil: schemes for farmers)
5. `"किसानों के लिए योजनाएं"` (Hindi: schemes for farmers)

Queries 4 and 5 must return relevant results — this validates that `multilingual-e5-small` handles Tamil and Hindi natively without any translation step at retrieval time.

Stop and show me results before Phase 4.

---

## PHASE 4 — RAG Answer Generation

### 4.1 Generator
Create `chatbot/backend/rag/generator.py`:

Function: `generate(query: str, retrieved_schemes: list[dict], language: str = "en") -> dict`

Returns:
```python
{
    "answer": str,
    "sources": [{"scheme_name": str, "section": str, "source_file": str}],
    "confidence": "high" | "medium" | "low",
    "language": str
}
```

System prompt must instruct the LLM:
- Answer ONLY from the retrieved scheme content provided below
- Every factual claim must name the scheme it came from
- If the answer is not found in the retrieved content, respond exactly: "I don't have reliable information on this. Please check the official MyScheme portal at myscheme.gov.in"
- Never guess, invent, or hallucinate scheme details, amounts, or eligibility criteria
- Confidence is "high" if answer is directly stated in content, "medium" if inferred, "low" if uncertain
- Format answer as clean readable paragraphs — not excessive bullet points
- Note: some scheme content may have FAQ text mixed into the benefits section due to a known data limitation — treat all content as valid scheme information regardless of which field it came from

### 4.2 RAG Chain
Create `chatbot/backend/rag/rag_chain.py`:

Function: `answer(query: str, language: str = "en") -> dict`
- Calls retriever → generator
- If `retrieved_schemes` is empty → return low confidence response directing to myscheme.gov.in
- Returns full response dict

Test with:
1. `"What documents do I need to apply for PM-KISAN?"` — must return grounded answer with source
2. `"What is the benefit amount for housing schemes for SC category?"` — must cite scheme name
3. `"Tell me about a scheme called XYZ123 that does not exist"` — must return graceful decline, not hallucination

Stop and show me all 3 test results before Phase 5.

---

## PHASE 5 — Intent Router + Eligibility Engine

### 5.1 Intent Classifier
Create `chatbot/backend/router/intent_classifier.py`:

Function: `classify(query: str) -> dict`

Returns:
```python
{
    "intent": "scheme_search" | "eligibility_check" | "document_upload" | "comparison" | "out_of_scope",
    "confidence": float,
    "extracted_entities": dict
}
```

Use deterministic keyword/pattern matching:
- `"am I eligible"`, `"do I qualify"`, `"can I apply"`, `"check eligibility"`, `"eligible for"` → `eligibility_check`
- `"upload"`, `"verify document"`, `"check my document"`, `"my certificate"` → `document_upload`
- `"compare"`, `"difference between"`, `"which is better"`, `"vs"` → `comparison`
- `"what is"`, `"tell me about"`, `"how to apply"`, `"schemes for"`, `"benefits of"`, `"documents required"` → `scheme_search`
- Anything not matching above → `out_of_scope`

Also extract entities from query:
- Age: `"I am 25 years old"`, `"age 30"` → `{"age": 25}`
- State: `"in Tamil Nadu"`, `"from Maharashtra"` → `{"state": "Tamil Nadu"}`
- Income: `"income of 1.5 lakhs"`, `"earn 2 lakh"` → `{"income": 150000}`
- Category: `"SC category"`, `"I am OBC"`, `"ST community"` → `{"category": "sc"}`

### 5.2 User Profile Schema
Create `chatbot/backend/eligibility/user_profile.py`:

Pydantic model `UserProfile`:
```python
age: Optional[int] = None
gender: Optional[str] = None        # male | female | other
state: Optional[str] = None
income_annual: Optional[float] = None
category: Optional[str] = None      # general | obc | sc | st
is_student: Optional[bool] = None
is_employed: Optional[bool] = None
occupation: Optional[str] = None
disability: Optional[bool] = None
is_ex_serviceman: Optional[bool] = None
```

### 5.3 Slot Filler
Create `chatbot/backend/eligibility/slot_filler.py`:

Function: `get_next_question(profile: UserProfile) -> str | None`
- Returns the next question to ask to complete the profile
- Returns None if profile has enough fields to attempt eligibility check
- Priority order: age → state → income → category → gender
- Questions must be natural and conversational, not form-like

### 5.4 Rules Engine
Create `chatbot/backend/eligibility/rules_engine.py`:

Function: `check_eligibility(profile: UserProfile, scheme: dict) -> dict`

Returns:
```python
{
    "eligible": bool,
    "reasons": [str],
    "failed_conditions": [str],
    "unverifiable_conditions": [str]
}
```

Extract and check rule types from `scheme["eligibility"]["conditions"]`:
- Age: regex for `"above X"`, `"below X"`, `"between X and Y"`, `"minimum age X"`, `"not exceeding X years"`
- Income: regex for `"below X lakhs"`, `"income not exceeding"`, `"BPL"`, `"APL"`, `"annual income less than"`
- Category: keyword match for `"SC"`, `"ST"`, `"OBC"`, `"general"`, `"women"`, `"differently abled"`, `"ex-serviceman"`
- State: match state name from conditions against profile state
- If a condition string cannot be parsed deterministically → add to `unverifiable_conditions`, never guess the result

Also check `scheme["eligibility"]["exclusions"]` — if any exclusion matches the profile, mark as ineligible with reason.

Test eligibility check on 3 real schemes from `test_output_unstructured/` with a known user profile. Show the full output dict for each.

Stop and show me results before Phase 6.

---

## PHASE 6 — Document Verification

### 6.1 OCR
Create `chatbot/backend/documents/ocr.py`:

Function: `extract_text(file_path: str) -> dict`

Returns:
```python
{
    "text": str,
    "method": "pymupdf" | "paddleocr",
    "confidence": float
}
```
- Try PyMuPDF first (fast, accurate for digital PDFs — same library already used in the extraction pipeline)
- If extracted text length < 100 characters, fall back to PaddleOCR for scanned documents
- Log which method was used

### 6.2 Structured Extractor
Create `chatbot/backend/documents/extractor.py`:

Pydantic model `DocumentFields`:
```python
name: Optional[str] = None
date_of_birth: Optional[str] = None
age: Optional[int] = None
income_annual: Optional[float] = None
category: Optional[str] = None
state: Optional[str] = None
aadhaar_last4: Optional[str] = None   # Last 4 digits ONLY
```

Each field also carries a confidence score (0.0–1.0) stored alongside it.

Function: `extract_fields(text: str) -> dict`
- Use Groq + Instructor to extract `DocumentFields` from OCR text
- Return fields with per-field confidence scores
- CRITICAL SECURITY RULE: Never store, log, or return a full 12-digit Aadhaar number under any circumstances. Extract only the last 4 digits. Mask immediately after extraction before any logging.

### 6.3 Auto-fill Logic
Function: `autofill_profile(extracted: dict, profile: UserProfile) -> dict`

Returns:
```python
{
    "updated_profile": UserProfile,
    "high_confidence_fills": [str],    # auto-filled without asking user
    "needs_confirmation": [str],        # show to user for confirmation
    "failed_fields": [str]              # could not extract, ask manually
}
```

Confidence thresholds:
- >= 0.85 → auto-fill silently
- 0.50–0.84 → fill but ask user: `"I found your income as ₹1,80,000. Is that correct?"`
- < 0.50 → do not fill, ask user manually

Test with a dummy income certificate string (create a sample text, not a real document):
```
"INCOME CERTIFICATE
Name: Rajesh Kumar
Date of Birth: 15/03/1990
Annual Income: Rs. 1,80,000
Caste: OBC
State: Tamil Nadu"
```

Show the full `autofill_profile` output for this test string.

Stop and show me results before Phase 7.

---

## PHASE 7 — Translation Layer

Create `chatbot/backend/translation/translator.py`:

### Language Detection
Function: `detect_language(text: str) -> str`
- Use `langdetect`
- Returns: `"en"` | `"ta"` | `"hi"` | `"unknown"`
- Default to `"en"` if detection confidence is low

### Translation
Use `googletrans` library (free, no API key needed):

Function: `translate(text: str, source_lang: str, target_lang: str) -> str`
- `"en"` → `"ta"` (English to Tamil)
- `"en"` → `"hi"` (English to Hindi)
- If source and target are the same, return text unchanged
- Handle translation failures gracefully — return original English text if translation fails, log the failure

### Pipeline Integration
IMPORTANT: `multilingual-e5-small` handles Tamil and Hindi queries natively at retrieval time — do NOT translate the user query before retrieval. Embed it directly.

Translation is only needed for the output:
1. Detect query language once at entry point
2. Pass `language` string through the entire pipeline
3. Translate the final English answer to user's language before returning
4. Never translate retrieved scheme content — keep it in English for the LLM

Test:
1. Tamil input: `"விவசாயிகளுக்கான திட்டங்கள் என்ன?"` → detect language → retrieve → generate English answer → translate to Tamil
2. Hindi input: `"किसानों के लिए क्या योजनाएं हैं?"` → detect → retrieve → generate → translate to Hindi
3. English input: `"What schemes are available for farmers?"` → detect → retrieve → generate → return English (no translation)

Stop and show me all 3 test results before Phase 8.

---

## PHASE 8 — FastAPI Backend

Create `chatbot/backend/api/main.py`:

### Endpoints
- `GET /health` → `{"status": "ok", "schemes_loaded": int, "embeddings_loaded": int}`
- `POST /profile` → accepts `UserProfile` JSON, stores in session, returns confirmation
- `POST /chat` → accepts `{"message": str, "session_id": str, "language": str}`, returns full response dict
- `WebSocket /ws/chat` → real-time chat, same logic as POST /chat

### Request Flow for Every Message
```
Receive message
      ↓
Detect language (langdetect)
      ↓
Classify intent (deterministic router)
      ↓
Route to handler:
  scheme_search   → RAG chain → translate answer
  eligibility_check → slot filler → rules engine → translate answer
  document_upload → OCR → extractor → autofill → translate confirmation
  comparison      → RAG chain with comparison prompt → translate answer
  out_of_scope    → fallback response with myscheme.gov.in link
      ↓
Return:
{
  "answer": str,
  "sources": list,
  "confidence": str,
  "intent": str,
  "language": str,
  "session_id": str
}
```

### Session Management
- Each `session_id` gets its own `UserProfile` and conversation history stored in an in-memory dict
- No database storage of conversations
- Session expires after 30 minutes of inactivity
- Generate `session_id` as UUID if not provided

### Security
- Input length limit: 1000 characters — reject with 400 if exceeded
- Basic prompt injection filter: reject messages containing `"ignore previous instructions"`, `"you are now"`, `"pretend you are"`, `"disregard your"` — return a polite decline
- Never return raw MongoDB `_id` or internal fields in responses
- CORS enabled for `http://localhost:5173` (Vite default)

Test end-to-end via Python `requests` (not frontend yet):
1. `POST /chat` with `"What schemes are available for farmers in Tamil Nadu?"`
2. `POST /chat` with `"Am I eligible? I am 30 years old, SC category, income 1.2 lakhs, from Tamil Nadu"`
3. WebSocket connection sending a Hindi query

Stop and show me all 3 test results before Phase 9.

---

## PHASE 9 — React Frontend

Create React app in `chatbot/frontend/` using Vite:
```
npm create vite@latest frontend -- --template react
cd frontend
npm install tailwindcss axios uuid
npx tailwindcss init
```

### Components to Build

**`ChatWindow`**
- Displays full conversation history
- Auto-scrolls to latest message
- Shows typing indicator (animated dots) while waiting for backend response

**`MessageBubble`**
- User messages: right-aligned, distinct color
- Bot messages: left-aligned, white/light background
- Bot messages include below the answer text:
  - Confidence badge: 🟢 High / 🟡 Medium / 🔴 Low
  - Collapsible source citations: scheme name + section (e.g. "PM-KISAN › eligibility")

**`InputBar`**
- Text input + send button (Enter key also sends)
- File upload button — triggers document verification flow when a PDF is selected
- Language selector toggle: EN / தமிழ் / हिंदी — stored in React state, sent with every message

**`EligibilityPanel`**
- Shown when intent is `eligibility_check`
- Displays collected `UserProfile` fields as the conversation fills them in
- Shows final eligible ✅ / ineligible ❌ result with reasons listed

**`SchemeCard`**
- Compact card shown for search results
- Shows: scheme name, one-line benefit summary, eligibility summary, source file name

### WebSocket Connection
- Connect to `ws://localhost:8000/ws/chat` on page load
- Generate `session_id` as UUID on load, persist in `localStorage`
- Send: `{"message": str, "session_id": str, "language": "en"|"ta"|"hi"}`
- Receive: `{"answer": str, "sources": list, "confidence": str, "intent": str}`
- Handle WebSocket disconnection gracefully — show reconnecting indicator

### Design Requirements (keep it clean, not flashy)
- Professional, minimal UI — this is a government scheme assistant, not a social app
- Mobile-responsive layout
- No animations beyond the typing indicator
- Tailwind utility classes only — no custom CSS files

Test: full end-to-end conversation in all 3 languages through the UI.

Stop and show me the working UI before Phase 10.

---

## PHASE 10 — Evaluation

### Test Query Dataset
Create `chatbot/evaluation/test_queries.json` with 50 test queries across these categories:

- 10 scheme search queries (English, Tamil, Hindi mix)
- 10 eligibility check queries with known correct answers
- 10 benefits/documents queries
- 10 out-of-scope queries (must be declined gracefully — no hallucination)
- 10 edge cases (ambiguous queries, partial info, misspelled scheme names, very short queries)

### RAG Evaluation
Create `chatbot/evaluation/eval_rag.py`:
- Run all 50 queries through the full pipeline
- Measure and report:
  - **Retrieval accuracy**: did the correct scheme appear in top 5 results? (manual spot-check on 10)
  - **Decline rate**: what % of out-of-scope queries were correctly declined rather than hallucinated?
  - **Average response time**: latency per query in seconds
  - **Source citation rate**: what % of answers include at least one source?

### Eligibility Evaluation
Create `chatbot/evaluation/eval_eligibility.py`:
- Define 20 test cases manually: `(UserProfile, scheme_name, expected_result: bool)`
- Use real schemes from `dataset/gov_myscheme/test_output_unstructured/`
- Run rules engine on each test case
- Report: accuracy %, how many were `unverifiable` (not a failure — expected for ambiguous rules)

### Evaluation Report
Create `chatbot/evaluation/EVAL_REPORT.md` and fill it with real numbers after running both scripts. This is what you quote in interviews:

```
RAG Evaluation (50 queries)
- Decline rate on out-of-scope: X%
- Source citation rate: X%
- Average response time: Xs

Eligibility Engine (20 test cases)
- Accuracy: X%
- Unverifiable conditions: X%
```

---

## PHASE 11 — Background: Complete PDF Processing

Run this independently whenever you have time — it does not block any chatbot phase:

```
Continue next 200
```

This runs `backend/extraction/batch_run_200.py` which processes the next 200 unprocessed PDFs from `dataset/gov_myscheme/unique_pdfs/`. Safe to stop and resume anytime.

Check page usage before each batch:
```
dataset/gov_myscheme/logs/page_usage.log
```
Free tier limit: 15,000 pages/month. Do not exceed this.

After all 2,066 PDFs are processed:
1. Run final schema validation: `python backend/extraction/validate_json.py`
2. Re-run `chatbot/backend/database/load_mongo.py` to ingest remaining schemes
3. Re-run `chatbot/backend/database/load_chroma.py` to embed remaining schemes
4. Merge `feature/unstructured-extraction` into `main` via PR on GitHub

---

## Stretch Goals (only after Phases 1–10 are complete and working)

### Scheme Comparison
- When intent is `comparison`, retrieve both named schemes
- Pass both to Groq with a structured comparison prompt
- Return a comparison table (scheme name, benefit, eligibility, how to apply)

### Conflict Detection
- Query MongoDB for schemes where `eligibility.exclusions` mentions other scheme names
- Build a simple conflict map in memory at startup
- Flag conflicts when a user matches multiple schemes simultaneously

### LangGraph Migration
- If the Python router in Phase 5 becomes too complex to maintain
- Migrate intent routing to LangGraph `StateGraph`
- The node structure maps directly: scheme_search → faq_node, eligibility_check → eligibility_node, etc.

---

## What to Say in Interviews

When recruiters ask about this project:

1. **Scale**: "I built a pipeline that processed 2,066 government scheme PDFs into structured JSON using the Unstructured API with a custom embedding classifier — no LLM in the extraction pipeline, fully deterministic."

2. **Retrieval**: "I used hybrid retrieval — MongoDB metadata filtering combined with ChromaDB semantic search using multilingual-e5-small, which handles Tamil and Hindi queries natively without a translation step."

3. **Reliability**: "Eligibility decisions are made by a deterministic rules engine, not the LLM. The LLM only explains the result in natural language. This eliminates hallucination risk on the most critical feature."

4. **Multilingual**: "Tamil and Hindi queries retrieve correctly without translation because the embedding model is multilingual. Only the output answer is translated."

5. **Evaluation**: Quote your actual Ragas scores and eligibility accuracy % from `EVAL_REPORT.md`.

6. **Engineering**: "I built LLM provider abstraction and embedding abstraction from the start, so switching models is a one-line config change."