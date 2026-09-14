# Project Plan: AI-Powered Government Scheme Assistance Chatbot

**Project Type:** Academic / Engineering Capstone Project
**Domain:** Conversational AI, RAG, Agentic Systems, Responsible AI
**Institution Context:** VIT Chennai

---

## 1. Problem Statement

Citizens in India often fail to benefit from government welfare schemes due to:
- Fragmented information spread across multiple portals
- Complex, inconsistent eligibility criteria
- No single tool to check eligibility, compare schemes, or detect conflicts between schemes
- Language and literacy barriers preventing access for rural/non-English speakers
- Manual application processes with no guided document verification

**Goal:** Build a chatbot that doesn't just answer "what is scheme X" (like most existing solutions), but actively determines eligibility, detects scheme conflicts, verifies documents, and communicates in regional languages — while remaining safe against hallucinated/incorrect eligibility claims.

---

## 2. Related Work Summary (Why This Project Is Novel)

| Existing Work | What It Does | What It Lacks |
|---|---|---|
| SchemeBot (IJRASET) | JSON-based Q&A with NLP (tokenization, BoW, lemmatization) + neural network responses | No dynamic eligibility check, no grounding/citation |
| Schemes Paaru! (IEEE) | GPT-4 Turbo based, text/audio input | Informational only, no eligibility reasoning |
| Smart Scheme Navigation System (Tamil Nadu) | Flask + NLTK + BERT + TensorFlow recommendation | No conflict detection, no verified language support |
| GovGuide AI (GitHub) | Knowledge-Graph-grounded Agentic RAG with hallucination verification | No document verification, no deterministic rules engine |
| AI-Powered Rules as Code (Digital Government Hub) | Found that **pure LLM-generated eligibility logic is unreliable** without a structured rules layer | Not a chatbot; theoretical study only |

**Conclusion drawn from literature:** No existing system combines a deterministic eligibility engine + grounded RAG + conflict detection + document-driven auto-fill + regional language support in one pipeline. This is the gap this project fills.

---

## 3. Novelty / Key Features

1. **Hybrid RAG + Deterministic Eligibility Engine**
   Eligibility is never decided by the LLM directly — a Pydantic-validated rules engine computes eligibility; the LLM only explains the result in natural language.

2. **Citation-Forced, Confidence-Scored Answers**
   Every factual claim about a scheme must be traceable to a retrieved document chunk. If ungrounded, the bot downgrades to "I'm not fully certain" instead of asserting.

3. **Scheme Conflict / Overlap Detection**
   A lightweight knowledge graph flags mutually exclusive or overlapping schemes (e.g., cannot avail two housing subsidies together).

4. **Document Verification & Auto-fill**
   User uploads Aadhaar / income certificate / caste certificate (dummy/sample docs) → OCR + Pydantic-validated structured extraction → auto-fills eligibility fields instead of manual Q&A, with confidence-gated confirmation for low-certainty fields.

5. **Regional Language Support**
   Tamil/Hindi input and output support — aspirational in most existing literature, rarely actually shipped.

6. (Stretch) **Agentic Follow-up**
   Bot can be asked to remind the user before an application deadline, using persisted conversational state.

---

## 4. System Architecture

```
User (Web/Mobile UI)
        ↓
React Frontend (chat UI, language toggle, file upload, voice input)
        ↓ WebSocket
FastAPI Backend (/ws/chat)
        ↓
Authentication → Input Guardrail (PII scrub, prompt-injection check, language detection)
        ↓
LangGraph Router (decides which node(s) to invoke)
        ↓
   ┌─────────────┬────────────────┬─────────────────┬───────────────────────┐
   │ FAQ/RAG     │ Eligibility    │ Conflict Check   │ Document Verification │
   │ Node        │ Node           │ Node             │ Node                  │
   └─────────────┴────────────────┴─────────────────┴───────────────────────┘
        ↓
Output Guardrail (grounding/citation check, confidence scoring, format check)
        ↓
Response Generation (LLM composes answer from validated data only)
        ↓
Translate back to user's language (if needed) → WebSocket → Frontend
```

### 4.1 Node Responsibilities

| Node | Function |
|---|---|
| FAQ/RAG | Answers general scheme questions via vector search + reranking + citation-forced generation |
| Eligibility | Slot-fills user profile (age, income, state, category) via Pydantic schema; runs against deterministic rules engine |
| Conflict Check | Cross-references matched schemes against a scheme-relationship graph for exclusivity/overlap warnings |
| Comparison/Ranking | If multiple schemes match, ranks and returns a comparison table |
| Document Verification | OCR + structured extraction from uploaded documents; auto-fills eligibility fields with confidence-gated confirmation |
| Human Handoff | Surfaces official portal/helpline link when confidence is low or query is out of scope |

---

## 5. Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React + Tailwind CSS, WebSocket client |
| Backend | FastAPI |
| Data Validation | Pydantic (used across inputs, tool outputs, eligibility fields, document extraction) |
| Orchestration | LangGraph (stateful multi-node agent routing) |
| Guardrails | Guardrails AI / NeMo Guardrails, custom regex/PII filters |
| RAG | LangChain retriever + Chroma or Qdrant (vector DB) + cross-encoder reranker |
| Eligibility Rules Engine | Pure Python / Pydantic-validated deterministic logic |
| Knowledge Graph (conflicts) | NetworkX (lightweight) or Neo4j (for visual demo) |
| OCR | Tesseract or PaddleOCR |
| Document Handling | pdf2image, PyMuPDF, Pillow |
| Structured Extraction | Instructor + Pydantic (LLM output forced into schema) |
| Translation | IndicTrans2 (open-source) or a translation API |
| Observability | LangSmith or Arize Phoenix |
| Deployment | Docker; Render/Railway/single VM (sufficient for academic scope) |

---

## 6. Data Requirements

- Official scheme documents (PDFs) for 5–10 real schemes to start:
  - PM-KISAN, PMAY, Ayushman Bharat, PM Ujjwala Yojana, one Tamil Nadu state scheme (e.g., a state housing/education scheme)
- Sample/dummy Aadhaar, income certificate, and caste certificate templates (synthetic, not real user data) for document verification testing
- A small manually curated scheme-relationship dataset for conflict detection (which schemes are known to be mutually exclusive/overlapping)

---

## 7. Privacy & Security Considerations

- Never store full Aadhaar numbers — mask to last 4 digits or use a one-way hash if deduplication is needed
- Process uploaded documents in-memory where possible; discard raw images after extraction unless the user opts to save them
- Explicit data-minimization principle: extract only fields needed for eligibility computation
- Use only synthetic/dummy documents for demo and testing — never real personal identity documents
- Input guardrail to prevent prompt injection and filter off-topic/toxic queries
- Rate limiting on API endpoints to prevent abuse

---

## 8. Evaluation Plan

| Aspect | Method |
|---|---|
| Retrieval quality | Ragas (faithfulness, relevance) on RAG responses |
| Eligibility accuracy | Manual test cases against known scheme eligibility rules (ground truth) |
| Hallucination rate | Compare grounded vs ungrounded claims across a test query set |
| OCR/extraction accuracy | Field-level accuracy against sample document ground truth |
| Conflict detection accuracy | Precision/recall against manually curated known conflicts |
| Language support quality | Manual review of Tamil/Hindi translation fidelity |
| Latency | Response time benchmarking under normal load |

---

## 9. Build Roadmap (Suggested Order)

**Phase 1 — Core RAG Foundation**
- Collect and preprocess 5–10 scheme PDFs
- Build vector store + retriever + citation-forced answer generation
- Basic FastAPI + React chat interface

**Phase 2 — Eligibility Engine**
- Define Pydantic schemas for user profile fields
- Build deterministic rules engine for the same 5–10 schemes
- Integrate as a LangGraph node with slot-filling conversation flow

**Phase 3 — Guardrails**
- Add input guardrail (PII/injection filtering)
- Add output guardrail (grounding check, confidence scoring)

**Phase 4 — Conflict Detection**
- Build a small scheme-relationship graph (NetworkX) for 2–3 known overlapping/exclusive scheme pairs
- Integrate conflict-check node into the pipeline

**Phase 5 — Document Verification**
- Build OCR + Pydantic extraction pipeline for Aadhaar/income/caste certificate (dummy docs)
- Add confidence-gated confirmation step
- Wire auto-fill into the Eligibility node

**Phase 6 — Regional Language Support**
- Add language detection + translation in/out (Tamil/Hindi)
- Test end-to-end multilingual conversation flow

**Phase 7 — Evaluation & Polish**
- Run evaluation suite (Ragas, manual accuracy checks)
- Polish UI (confidence badges, source citations shown to user)
- Prepare demo script covering both happy-path and failure-handling cases

**Phase 8 (Stretch) — Agentic Follow-up**
- Add deadline reminder capability using persisted LangGraph state

---

## 10. Demo Script Outline (for viva/presentation)

1. General scheme question → show RAG answer with citation + confidence badge
2. Eligibility Q&A flow → show deterministic result ("eligible because X, ineligible because Y")
3. Upload a dummy Aadhaar/income certificate → show auto-filled eligibility fields with confidence confirmation
4. Trigger a known scheme conflict → show the warning message
5. Ask a question in Tamil/Hindi → show translated response
6. Deliberately ask an ungrounded/out-of-scope question → show the bot declining to guess and surfacing an official source instead

---

## 11. Report Structure Mapping

| Report Section | Maps to Plan Section |
|---|---|
| Introduction & Problem Statement | Section 1 |
| Literature Review / Related Work | Section 2 |
| Proposed System / Novelty | Section 3 |
| System Architecture | Section 4 |
| Implementation / Tech Stack | Section 5, 6 |
| Security & Ethical Considerations | Section 7 |
| Results & Evaluation | Section 8 |
| Conclusion & Future Work | Section 9 (Phase 8 stretch goal), overall novelty recap |

---

## 12. Open Risks / Things to Watch

- OCR accuracy on low-quality scanned documents may need fallback to manual entry
- Scheme rules can be legally ambiguous/inconsistent — document assumptions clearly in the report
- Translation quality for regional languages may need manual review, not just automated metrics
- Scope creep risk: prioritize Phases 1–4 as the guaranteed deliverable; treat Phases 5–8 as stretch depending on time
