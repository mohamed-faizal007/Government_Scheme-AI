# Government Scheme AI — Complete Project Plan

> **Project Type:** NLP / Information Extraction / Large Language Models  
> **Current Stage:** Extraction pipeline evaluation and model comparison  
> **Dataset:** 2,066 unique government scheme PDFs

---

# 1. Project Overview

## Project Title

**Government Scheme AI: An NLP-Based Information Extraction and Intelligent Scheme Discovery System**

## Main Goal

Build an NLP-based system that converts thousands of unstructured Indian government scheme documents into a clean, standardized, structured dataset.

The final system is intended to support:

- Government scheme search
- Semantic search
- Scheme recommendation
- Eligibility-based discovery
- Question answering
- Retrieval-Augmented Generation (RAG)
- An intelligent government scheme chatbot

---

# 2. The Core Problem

Government scheme information is spread across webpages and documents with inconsistent structures.

Different schemes may use different headings.

For example:

### Scheme A
- Benefits
- Eligibility
- Documents Required

### Scheme B
- Financial Assistance
- Who Can Apply
- Required Documents

### Scheme C
- Objectives
- Support Available
- Application Procedure

A simple rule-based system cannot reliably handle all these variations.

The system therefore needs to understand the **meaning** of sections and map them into a common structure.

---

# 3. Project Objective

The pipeline should:

1. Read government scheme PDFs.
2. Extract machine-readable text.
3. Remove webpage and PDF noise.
4. Normalize messy content.
5. Handle inconsistent section names.
6. Use an LLM for semantic extraction.
7. Convert content into standardized JSON.
8. Validate the JSON.
9. Save clean outputs for database and RAG usage.

---

# 4. Dataset

## Original Dataset

Total PDFs:

```text
2876
```

## Duplicate Removal

After duplicate detection:

```text
Total PDFs       : 2876
Unique PDFs      : 2066
Duplicate PDFs   : 810
```

## Working Dataset

```text
dataset/gov_myscheme/unique_pdfs/
```

The 2,066 PDFs were additionally checked for:

- Duplicate filenames
- Duplicate document contents

Results:

```text
No possible duplicate filenames found.
No duplicate document contents found.
```

Therefore, the current working dataset contains:

> **2,066 verified unique PDFs**

---

# 5. Dataset Characteristics

Based on the PDFs tested so far, the dataset primarily contains:

- Digitally generated PDFs
- Text-based PDFs
- Machine-readable text
- Government scheme webpages exported or saved as PDFs

The dataset is generally **not**:

- Scanned documents
- Image-only PDFs
- OCR-only documents

Therefore, OCR should **not** be in the normal processing path.

However, OCR can be added later as a fallback.

---

# 6. Main Dataset Challenges

The biggest challenge is not OCR.

The main challenge is:

> **Webpage-generated PDF content mixed with actual scheme information.**

Examples of unwanted content:

```text
Sign In
Sign Out
Cancel
Back
Apply Now
Check Eligibility
Something went wrong
Was this helpful?
```

Other issues include:

## 6.1 Bad Spacing

Examples:

```text
DetailsIntroduction
ApplicationProcess
DocumentsRequired
```

## 6.2 Encoding Artifacts

Examples:

```text
â€œ
â€
&amp;
```

## 6.3 Repeated Content

Some webpage PDFs may contain repeated sections.

## 6.4 Inconsistent Headings

For example:

```text
Benefits
Financial Assistance
Support Available
Assistance Provided
```

may all represent the same semantic concept.

---

# 7. Standard JSON Schema

The goal is to convert every scheme into a common structure.

Example:

```json
{
  "scheme_name": null,
  "description": null,
  "objectives": [],
  "benefits": [],
  "eligibility": [],
  "exclusions": [],
  "application_process": [],
  "documents_required": [],
  "faqs": [],
  "sources": []
}
```

A Pydantic schema already exists in:

```text
backend/extraction/schema.py
```

The system should use schema validation before saving output.

---

# 8. Project Structure

Important project structure:

```text
Government_Scheme-AI/

├── PROJECT_PLAN.md
│
├── backend/
│   │
│   ├── extraction/
│   │   ├── batch_extract.py
│   │   ├── extract_text.py
│   │   ├── preprocess.py
│   │   ├── postprocess.py
│   │   ├── prompts.py
│   │   ├── schema.py
│   │   ├── validate_json.py
│   │   │
│   │   ├── test_ollama.py
│   │   ├── test_docling.py
│   │   ├── test_docling_qwen.py
│   │   └── test_docling_groq.py
│   │
│   └── scripts/
│       ├── remove_duplicates.py
│       ├── check_duplicate_content.py
│       └── check_possible_duplicates.py
│
├── dataset/
│   └── gov_myscheme/
│       ├── unique_pdfs/
│       ├── json_output/
│       ├── logs/
│       └── docling_test/
│
├── venv/
│
└── .env
```

Some files may change as experiments are finalized.

---

# 9. Git Repository

Correct repository:

```text
C:\Faizal\Government_Scheme-AI
```

GitHub remote:

```text
https://github.com/mohamed-faizal007/Government_Scheme-AI.git
```

Before making changes, verify:

```powershell
git rev-parse --show-toplevel
git branch --show-current
git remote -v
git status
```

Expected project root:

```text
C:/Faizal/Government_Scheme-AI
```

---

# 10. Initial Extraction Pipeline

The first working approach used Gemini.

Architecture:

```text
PDF
 ↓
Text Extraction
 ↓
Preprocessing
 ↓
Gemini API
 ↓
Structured JSON
 ↓
Pydantic Validation
 ↓
Save JSON
```

Model:

```text
gemini-2.5-flash
```

---

# 11. Gemini Pipeline Status

Gemini extraction successfully processed test batches.

One batch result:

```text
10 PDFs processed
10 successful
0 failed
```

The pipeline supports:

- Batch processing
- Retry logic
- Error logging
- Resume support
- Skipping already processed PDFs
- ETA calculation

Resume logic:

```text
Does JSON exist?
    │
    ├── Yes → Skip
    │
    └── No → Process
```

This means completed work is preserved.

---

# 12. Gemini Limitations

Gemini produced successful results, but the free API introduced problems:

- Quota exhaustion
- Temporary 503 errors
- Rate limits
- Cloud dependency
- Risk of interruption during 2,066 PDF processing

Example:

```text
GEMINI FREE API QUOTA REACHED
```

Therefore, Gemini is not automatically the best option for processing the full dataset.

---

# 13. Local LLM Backup Plan

A local LLM pipeline was selected as a backup.

Architecture:

```text
Python
 ↓
Ollama
 ↓
Qwen 2.5 3B
 ↓
Structured JSON
```

Advantages:

- No API quota
- No per-request cost
- Local execution
- Full control
- No cloud dependency for inference

Disadvantages:

- Can be slow on CPU
- Uses local RAM
- Uses disk storage
- Processing 2,066 PDFs may take significant time

---

# 14. Ollama Status

Ollama was installed successfully.

Verified version:

```text
ollama version is 0.32.14
```

---

# 15. Qwen Status

Downloaded model:

```text
qwen2.5:3b
```

Approximate model download:

```text
1.9 GB
```

Command used:

```powershell
ollama pull qwen2.5:3b
```

The model download completed successfully.

---

# 16. Python Environment Issue

The previous virtual environment was broken because it referenced:

```text
C:\Python312\python.exe
```

but the active system Python installation was:

```text
Python 3.13.1
C:\Python313\python.exe
```

The virtual environment was recreated.

Current activation command:

```powershell
.\venv\Scripts\Activate.ps1
```

Verify:

```powershell
python --version
```

---

# 17. OpenAI-Compatible Client

The Python OpenAI client can be used as a compatible API client.

For Ollama:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)
```

Important:

> This does not mean OpenAI models are running locally.

It only uses an OpenAI-compatible API format.

---

# 18. Docling Experiment

Docling was tested as an alternative PDF parser.

Pipeline:

```text
PDF
 ↓
Docling
 ↓
Markdown
 ↓
Text
```

Test script:

```text
backend/extraction/test_docling.py
```

Test outputs:

```text
dataset/gov_myscheme/docling_test/
```

Docling successfully converted PDFs into:

- Markdown
- Text

---

# 19. Docling Conclusion

Docling successfully parses the document, but it does not automatically solve all problems.

Docling output can still contain:

```text
Sign In
Cancel
Back
Apply Now
Check Eligibility
Something went wrong
```

It may also preserve spacing/layout issues.

Therefore:

> **Docling is a parser, not a complete information extraction solution.**

It may still be useful as part of the pipeline.

---

# 20. Current Experimental Pipelines

## Pipeline A — Gemini

```text
PDF
 ↓
Text Extraction
 ↓
Preprocessing
 ↓
Gemini 2.5 Flash
 ↓
Validation
 ↓
JSON
```

Status:

```text
Working
```

Main problem:

```text
Free API quota
```

---

## Pipeline B — Docling + Qwen

```text
PDF
 ↓
Docling
 ↓
Markdown/Text
 ↓
Preprocessing
 ↓
Qwen 2.5 3B via Ollama
 ↓
JSON
 ↓
Validation
```

Status:

```text
Experimental
```

Main advantage:

```text
No cloud API quota
```

Main concern:

```text
Speed and extraction accuracy
```

---

## Pipeline C — Docling + Groq

```text
PDF
 ↓
Docling
 ↓
Markdown/Text
 ↓
Groq LLM
 ↓
Structured JSON
 ↓
Validation
```

Status:

```text
Experimental / testing
```

Potential advantages:

- Fast inference
- Strong cloud models
- OpenAI-compatible API

Potential risks:

- Rate limits
- Cloud dependency
- API limits

---

# 21. Role of the LLM

The LLM should not simply summarize the document.

Its job is:

> **Semantic Information Extraction + Normalization + Schema Mapping**

Example:

```text
Who Can Apply
```

should map to:

```json
"eligibility": []
```

Example:

```text
Financial Assistance
```

should map to:

```json
"benefits": []
```

Example:

```text
Required Documents
```

should map to:

```json
"documents_required": []
```

The source headings may vary.

The output schema should remain consistent.

---

# 22. Preprocessing Requirements

The preprocessing layer should handle:

- Extra whitespace
- Repeated spaces
- Broken lines
- Encoding artifacts
- HTML entities
- Website UI noise
- Repeated content
- Navigation elements
- Footer noise

However, preprocessing must be conservative.

Do not blindly delete text simply because it contains a keyword.

---

# 23. Noise Removal

Common webpage noise may include:

```text
Sign In
Sign Out
Cancel
Back
Apply Now
Check Eligibility
Something went wrong
Was this helpful?
Share
News and Updates
```

Recommended approach:

```text
Raw Text
 ↓
Normalize
 ↓
Detect likely UI blocks
 ↓
Remove high-confidence noise
 ↓
Preserve uncertain content
```

---

# 24. Duplicate Content Handling

Some PDFs may repeat content internally.

Potential pipeline:

```text
Extract Text
 ↓
Normalize Whitespace
 ↓
Split Into Chunks
 ↓
Compare Chunks
 ↓
Detect Repetition
 ↓
Remove High-Confidence Duplicates
```

Do not aggressively remove repeated text without checking context.

---

# 25. Hallucination Prevention

Prompts must explicitly state:

```text
Do not invent information.
```

If information is not present:

```text
Use null
```

or:

```text
Use []
```

Do not allow the model to guess missing requirements.

Example:

Bad:

```text
This scheme probably requires Aadhaar.
```

Good:

```json
"documents_required": []
```

when documents are not mentioned.

---

# 26. Validation Pipeline

Every output should follow:

```text
LLM Response
 ↓
JSON Parsing
 ↓
Pydantic Schema Validation
 ↓
Postprocessing
 ↓
Save
```

If validation fails:

```text
Retry
 ↓
If still invalid
 ↓
Log Error
 ↓
Do Not Save Corrupted Output
```

---

# 27. Batch Processing Requirements

The final batch system must support:

- Selected batch sizes
- Resume capability
- Skip completed files
- Retries
- Error logging
- Safe interruption
- Progress tracking
- ETA estimation
- No unnecessary overwrites

---

# 28. Retry Strategy

Temporary failures may include:

- 503 errors
- 429 errors
- Timeouts
- Network errors
- Invalid model responses

Recommended strategy:

```text
Attempt
 ↓
Failure
 ↓
Wait
 ↓
Retry
 ↓
Longer Wait
 ↓
Retry
```

Example exponential backoff:

```text
10 seconds
20 seconds
40 seconds
80 seconds
```

---

# 29. Error Logging

Current log location:

```text
dataset/gov_myscheme/logs/
```

Example:

```text
extraction_errors.log
```

Log:

- PDF filename
- Error message
- Traceback
- Timestamp if available

---

# 30. Testing Strategy

Do not process all 2,066 PDFs immediately.

Correct testing sequence:

```text
1 PDF
 ↓
Validate
 ↓
5 PDFs
 ↓
Validate
 ↓
20 PDFs
 ↓
Validate
 ↓
100 PDFs
 ↓
Validate
 ↓
Full Dataset
```

This prevents wasting time processing thousands of documents with a bad pipeline.

---

# 31. Evaluation Criteria

Every pipeline should be evaluated using the same PDFs.

Compare:

## 1. JSON Validity

Can Python parse the JSON?

## 2. Schema Validity

Does the output match the Pydantic schema?

## 3. Scheme Name Accuracy

Was the correct scheme identified?

## 4. Benefits Accuracy

Were actual benefits extracted?

## 5. Eligibility Accuracy

Were eligibility conditions preserved?

## 6. Numerical Accuracy

Check:

- Percentages
- Amounts
- Dates
- Age limits
- Income limits

## 7. Noise Handling

Check that UI noise is not extracted as scheme data.

## 8. Hallucination

Check whether the model invented information.

## 9. Speed

Measure:

```text
Seconds per PDF
```

Then estimate total processing time for:

```text
2066 PDFs
```

---

# 32. Important Design Decision

Do not select a model based only on speed.

Priority should be:

1. Extraction accuracy
2. Hallucination rate
3. JSON/schema validity
4. Numerical accuracy
5. Reliability
6. Processing speed
7. Cost/API limitations

A fast model producing incorrect scheme data is worse than a slower model producing reliable data.

---

# 33. Recommended Final Architecture

```text
                     GOVERNMENT SCHEME PDF
                              │
                              ▼
                      PDF PARSER LAYER
                      ┌──────────────┐
                      │ PyMuPDF      │
                      │ or Docling   │
                      └──────┬───────┘
                             │
                             ▼
                         RAW CONTENT
                             │
                             ▼
                      PREPROCESSING
                      ┌──────────────┐
                      │ UI Noise     │
                      │ Whitespace   │
                      │ Encoding     │
                      │ Duplicates   │
                      └──────┬───────┘
                             │
                             ▼
                        CLEAN CONTENT
                             │
                             ▼
                      LLM EXTRACTION
                      ┌──────────────┐
                      │ Gemini       │
                      │ Qwen         │
                      │ Groq         │
                      └──────┬───────┘
                             │
                             ▼
                       STRUCTURED JSON
                             │
                             ▼
                       VALIDATION
                             │
                     ┌───────┴───────┐
                     │               │
                   VALID           INVALID
                     │               │
                     ▼               ▼
                  SAVE JSON       RETRY/LOG
```

---

# 34. OCR Fallback

OCR should remain outside the normal pipeline.

```text
PDF
 │
 ▼
Can meaningful text be extracted?
 │
 ├── YES
 │     ↓
 │ Normal Pipeline
 │
 └── NO
       ↓
      OCR
       ↓
 Normal Pipeline
```

OCR may be needed later for:

- Scanned PDFs
- Image-only documents
- Poorly encoded files

---

# 35. Immediate Current Task

The current task is:

> **Compare extraction approaches before scaling to the full dataset.**

The experiments are:

```text
Docling → Qwen
```

and:

```text
Docling → Groq
```

These should be compared against the already tested:

```text
Gemini pipeline
```

Use the same sample PDF wherever possible.

---

# 36. Immediate Next Steps

## Step 1

Run:

```text
test_docling_qwen.py
```

Evaluate:

- JSON validity
- Accuracy
- Speed
- Noise handling
- Hallucination

---

## Step 2

Run:

```text
test_docling_groq.py
```

Evaluate the same criteria.

---

## Step 3

Compare:

```text
Gemini
vs
Qwen
vs
Groq
```

Use the original PDF as the source of truth.

---

## Step 4

Select the best approach based on evidence.

Do not choose based on assumptions.

---

## Step 5

Create a separate batch pipeline for the selected approach.

Do not immediately overwrite:

```text
batch_extract.py
```

Examples:

```text
batch_extract_groq.py
```

or:

```text
batch_extract_local.py
```

---

## Step 6

Test the new batch pipeline:

```text
5 PDFs
```

---

## Step 7

Then:

```text
20 PDFs
```

---

## Step 8

Then:

```text
100 PDFs
```

Measure:

- Accuracy
- Failures
- Speed
- Invalid JSON
- Hallucination
- Noise extraction

---

## Step 9

Only after successful validation:

```text
Process all 2066 PDFs
```

---

# 37. After Dataset Extraction

The future pipeline is:

```text
2066 PDFs
 ↓
Structured JSON Dataset
 ↓
Database
 ↓
Embedding Generation
 ↓
Vector Database
 ↓
Semantic Retrieval
 ↓
RAG
 ↓
Government Scheme Chatbot
```

---

# 38. Future User Query Example

A user may ask:

```text
I am a student from Tamil Nadu.
What government schemes am I eligible for?
```

Future workflow:

```text
User Query
 ↓
Understand Requirements
 ↓
Retrieve Relevant Schemes
 ↓
Check Eligibility Information
 ↓
Rank Results
 ↓
Generate Answer
```

---

# 39. Possible Database

MongoDB is a possible option because the data naturally contains:

- Nested fields
- Arrays
- Variable detail levels

Example:

```json
{
  "scheme_name": "...",
  "benefits": [],
  "eligibility": [],
  "documents_required": []
}
```

---

# 40. Future RAG Architecture

```text
Scheme JSON
 ↓
Text Preparation
 ↓
Chunking
 ↓
Embeddings
 ↓
Vector Database

User Query
 ↓
Query Embedding
 ↓
Semantic Search
 ↓
Relevant Schemes
 ↓
LLM
 ↓
Final Answer
```

---

# 41. Security Rules

Never hardcode API keys.

Bad:

```python
API_KEY = "secret_key"
```

Good:

```python
import os

API_KEY = os.getenv("GROQ_API_KEY")
```

Use:

```text
.env
```

Ensure `.env` is included in:

```text
.gitignore
```

Never commit API keys to GitHub.

---

# 42. Rules for Future Development

## Rule 1

Do not modify the production extraction pipeline while testing experimental models.

Create separate test files first.

## Rule 2

Do not process all 2,066 PDFs before validation.

## Rule 3

Do not hardcode API keys.

## Rule 4

Do not assume every scheme has the same headings.

## Rule 5

Do not assume Docling solves webpage noise automatically.

## Rule 6

Do not put OCR in the normal pipeline without evidence.

## Rule 7

Do not blindly remove text based on keywords.

## Rule 8

Do not save invalid JSON.

## Rule 9

Do not overwrite successful output unnecessarily.

## Rule 10

Always compare extracted information with the original document during evaluation.

---

# 43. Success Criteria

The extraction pipeline is ready when it can consistently produce:

```text
✓ Valid JSON
✓ Schema validation passes
✓ Correct scheme name
✓ Correct benefits
✓ Correct eligibility
✓ Correct application information
✓ Important numbers preserved
✓ Minimal hallucination
✓ Webpage noise ignored
✓ Acceptable processing speed
✓ Resume after interruption
✓ Proper error logging
✓ Works across different document structures
```

---

# 44. Current Project Status

## Completed

### Dataset

```text
[✓] Dataset collected
[✓] Duplicate PDFs removed
[✓] Filename duplicates checked
[✓] Content duplicates checked
[✓] 2066 unique PDFs prepared
```

### Gemini

```text
[✓] Gemini extraction implemented
[✓] Batch processing implemented
[✓] Resume logic implemented
[✓] Retry logic implemented
[✓] Error logging implemented
[✓] Sample PDFs successfully processed
```

### Ollama / Qwen

```text
[✓] Ollama installed
[✓] Qwen 2.5 3B downloaded
[✓] Python environment repaired
[✓] Local LLM testing started
```

### Docling

```text
[✓] Docling tested
[✓] PDF converted to Markdown
[✓] PDF converted to Text
[✓] Noise issue identified
```

---

# 45. Work Currently In Progress

```text
[ ] Validate Docling → Qwen extraction
[ ] Validate Docling → Groq extraction
[ ] Compare Gemini vs Qwen vs Groq
[ ] Select final extraction pipeline
[ ] Build dedicated batch pipeline
[ ] Validate on 5 PDFs
[ ] Validate on 20 PDFs
[ ] Validate on 100 PDFs
[ ] Process all 2066 PDFs
```

---

# 46. Final Project Vision

Transform:

```text
Thousands of messy government scheme PDFs
```

into:

```text
A structured, searchable,
NLP-powered government scheme knowledge system.
```

Final architecture:

```text
Government Scheme PDFs
        ↓
Document Parsing
        ↓
Text Cleaning
        ↓
LLM Information Extraction
        ↓
Structured JSON Dataset
        ↓
Database + Embeddings
        ↓
Semantic Search / RAG
        ↓
Government Scheme AI Assistant
```

---

# 47. Current Starting Point for the Next AI / Developer

If continuing this project, start here:

1. Check the current Git branch and status.
2. Do not modify existing working Gemini extraction code yet.
3. Run and inspect the Qwen extraction experiment.
4. Run and inspect the Groq extraction experiment.
5. Compare outputs against the original PDF.
6. Select the best approach based on accuracy, hallucination, reliability, and speed.
7. Build a separate batch extraction pipeline.
8. Scale gradually: 5 → 20 → 100 → 2066 PDFs.
9. After structured data is reliable, move to database, embeddings, RAG, and chatbot development.

---

# END OF PROJECT PLAN
