# Work Report — Government Scheme AI

> Audit date: 2026-09-06
> Branch: `feature/local-llm-extraction`
> Plan audited against: `docs/Government_Scheme_AI_PROJECT_PLAN.md` (untracked — not in git; see Risks)
> Method: every claim below was checked against the actual file contents, actual dataset counts, and (where possible) actual execution — not against the plan's own status tables.

---

## 1. Summary

The project has a genuinely working, evidence-backed **Gemini extraction pipeline** and a genuinely working, evidence-backed **duplicate-detection/dataset-prep pipeline** — both produce real, high-quality output that I inspected directly. Beyond that, the plan overstates progress. The three-way comparison (Gemini vs. Qwen vs. Groq) that the plan calls "the current task" has not actually happened: `test_docling_groq.py` is a **0-byte empty file**, and `test_docling_qwen.py`, while fully written (365 lines, well-structured), has **no corresponding output anywhere in the repo** — there is no `25-ciss_qwen.json`, no log, no evidence it ever completed a run. Only 17 of 2,066 PDFs (0.8%) have been processed end-to-end, and that run was halted by a Gemini quota error, not by a deliberate checkpoint. Two other stub files (`validate_json.py`, `requirements.txt`) are also completely empty despite being referenced as if they exist. Most seriously, **the currently active `venv/` cannot even run the Gemini pipeline** — it is missing `fitz` (PyMuPDF) and `google-genai`, so `batch_extract.py` would crash immediately with `ModuleNotFoundError` if invoked today, and there is no `requirements.txt` to reconstruct a working environment. I also found and reproduced a live data-corruption bug in `preprocess.py` (a blind substring removal turns "Engineer" into "ineer" and "England" into "land") that directly violates the plan's own Rule 7. The project's actual position is: dataset prep is solid and finished; the Gemini path works but its environment has bit-rotted; the "compare three pipelines, then scale" step the plan calls urgent has barely started.

---

## 2. Verified Completed

These are plan-section-44 items I confirmed by direct inspection, with evidence.

| Item | Evidence |
|---|---|
| Dataset collected (2,876 total) | `dataset/gov_myscheme/text_data/` contains exactly 2,876 PDFs; matches `dataset/reports/summary.txt`: "Total PDFs : 2876" |
| Duplicate PDFs removed (810 removed → 2,066 unique) | `backend/scripts/remove_duplicates.py` is a complete, functional SHA-256 hashing script; `dataset/gov_myscheme/unique_pdfs/` contains exactly **2,066** files — exact match to the plan's claim |
| Filename duplicates checked | `backend/scripts/check_possible_duplicates.py` exists and is fully implemented (suffix-normalization + grouping) |
| Content duplicates checked | `backend/scripts/check_duplicate_content.py` exists and is fully implemented (PyMuPDF text extraction + SHA-256 content hash) |
| Gemini extraction implemented | `backend/extraction/batch_extract.py` — real `genai.Client`, `Scheme` Pydantic schema, `response_schema` enforcement |
| Batch processing implemented | `batch_extract.py:75-92` — interactive batch-size prompt, slices `remaining_pdfs[:batch_size]` |
| Resume / skip-completed logic implemented | `batch_extract.py:50-59` — skips any PDF whose `OUTPUT_FOLDER/{stem}.json` already exists |
| Retry logic implemented | `batch_extract.py:231-241` — exponential backoff (`10 * 2**(retry-1)`, capped at 300s), 5 retries, plus a dedicated quota/429 branch that exits cleanly (`batch_extract.py:206-225`) |
| Error logging implemented | `dataset/gov_myscheme/logs/extraction_errors.log` exists and contains one real, dated quota-exhaustion entry ("Stopped at PDF: aay-goa copy.pdf", HTTP 429 RESOURCE_EXHAUSTED) |
| Sample PDFs successfully processed | `dataset/gov_myscheme/json_output/` contains **17** JSON files (not "batches," one partial run). I opened `25-ciss copy.json` in full — it correctly identifies the scheme name, state, department, benefits, eligibility, exclusions, documents, and 12 FAQ entries, matching the source PDF |
| Docling tested, PDF → Markdown/Text | `dataset/gov_myscheme/docling_test/25-ciss_copy.md` and `.txt` exist (12.6KB / 12.6KB, dated Aug 19), and are real Docling output, not placeholders |
| Docling noise issue identified | Confirmed directly — the markdown output I read is full of "Sign In", "Cancel", "Something went wrong. Please try again later.", footer boilerplate, etc., exactly as the plan describes |
| No hardcoded API keys / `.env` not committed | `git ls-files` (21 tracked files) does not include `.env`; `git grep` for `sk-`, `AIza`, `gsk_`-style key patterns across tracked history found nothing; `.env` correctly listed in `.gitignore` |

Not independently verifiable from the repo (system-level, no artifact left behind): Ollama installation, Qwen model download. I did not run `ollama --version` since that's outside repo scope — these are plausible but unverifiable from code/data alone.

---

## 3. Claimed but Unverified or Incomplete

| Plan claim | Reality |
|---|---|
| "Local LLM testing started" (section 44) | `test_ollama.py` is a legitimate, complete 50-line smoke test, but there is no captured output/log anywhere confirming it was ever run successfully — no artifact survives a run of this script by design (it only prints to stdout) |
| `validate_json.py` exists as part of the pipeline (section 8 file tree) | File exists but is **completely empty (0 bytes)**. Whatever validation happens is duplicated inline inside `batch_extract.py` and `extract_to_json.py` (`Scheme.model_validate_json(...)`) — there is no shared/reusable validation module despite one being listed in the architecture |
| Standard JSON Schema (section 7) — flat schema with `scheme_name`, `benefits`, `eligibility`, etc. | The actual `backend/extraction/schema.py` implements a **different, nested** schema (`Metadata`, `Overview`, `Benefits`, `Eligibility`, `Application`, `Support`, `FAQ`, `SearchMetadata`) — the plan's own documented schema and the shipped schema have diverged and no longer match |
| Encoding artifacts (section 6.2: `â€œ`, `â€`, `&amp;`) are a known issue being handled | Confirmed **not fixed**. I opened the real output `dataset/gov_myscheme/json_output/25-ciss copy.json` and it still contains `â€œ25% Capital Investment Subsidy Schemeâ€?` and `â‚¹6.25 lakhs` verbatim in saved output. `postprocess.py:clean_string` only strips control characters and zero-width characters — it never decodes mojibake or unescapes HTML entities |
| `test_docling_qwen.py` — "Validate Docling → Qwen extraction" | Script is fully written and reasonably careful (character-limits input, strips markdown fences, validates JSON, checks for the 10 expected schema fields) — but **no output file exists**. `dataset/gov_myscheme/docling_test/` has only the Docling `.md`/`.txt` files, no `25-ciss_qwen.json`. A stray `test_docling_qwen.cpython-313-pytest-9.1.1.pyc` in `__pycache__` suggests it was once imported by `pytest` (which would execute its top-level code as a side effect of collection), but that leaves no evidence the run completed or succeeded |
| `test_docling_groq.py` — "Docling + Groq" experimental pipeline | File is **entirely empty (0 bytes)**. This is not "experimental / testing" as plan section 20 claims — it has not been started at the code level at all |
| `backend/requirements.txt` | Tracked in git, but **0 bytes**. There is no dependency manifest for a project that uses `google-genai`, `pymupdf`, `pydantic`, `python-dotenv`, `docling`, and `openai` |
| Environment currently supports the Gemini pipeline | **False.** I ran `pip list` inside the active `venv/`: it has `docling`, `openai`, `pydantic`, `python-dotenv` (116 packages total) but **no `fitz`/`pymupdf` and no `google-genai`**. Running `batch_extract.py`, `extract_text.py`, or `extract_to_json.py` today would fail immediately with `ModuleNotFoundError`. The environment currently only supports the Docling/Ollama experimental path, not the "working" Gemini path |
| `backend/config/ui_noise_patterns.txt` (33 curated noise phrases) is part of the preprocessing pipeline | `git grep -r "ui_noise_patterns"` across `backend/` returns **zero matches** — this file is never loaded or referenced by any code. `preprocess.py` instead uses its own hardcoded, shorter `REMOVE_PHRASES` list (19 entries) that duplicates a subset of it |

---

## 4. In Progress (real status vs. plan section 45)

| Plan item | Real status |
|---|---|
| Validate Docling → Qwen extraction | **Not validated.** Code exists; no output artifact exists to validate |
| Validate Docling → Groq extraction | **Not started.** File is empty |
| Compare Gemini vs Qwen vs Groq | **Cannot happen yet** — only one of the three (Gemini) has actual saved output to compare |
| Select final extraction pipeline | **Not done** — no decision recorded anywhere (no notes, no new batch file, no README update) |
| Build dedicated batch pipeline (`batch_extract_groq.py` / `batch_extract_local.py`) | **Not done** — neither file exists anywhere in the repo or working tree |
| Validate on 5 / 20 / 100 PDFs | **N/A** — blocked on the item above; no such runs could have happened |
| Process all 2,066 PDFs | **17 / 2,066 done (0.8%)**, and that run stopped due to a Gemini quota error, not a deliberate stage-gate per the plan's own 1→5→20→100→2066 testing ladder (section 30) |

---

## 5. Gap Analysis — Plan Section 36, Steps 1–9

**Step 1 — Run `test_docling_qwen.py`:** Code is ready and well-built. **Not confirmed executed to completion** — no `25-ciss_qwen.json` output exists in `dataset/gov_myscheme/docling_test/`. Blocking: needs Ollama running locally with `qwen2.5:3b` pulled, and the current `venv/` does have `openai` (compatible client) so this should be runnable — the gap is simply that it hasn't been run-and-captured yet.

**Step 2 — Run `test_docling_groq.py`:** **Blocked at the starting line** — the file is empty. Needs to be written: load the Docling markdown (reuse pattern from `test_docling_qwen.py`), call Groq's OpenAI-compatible endpoint, and a `GROQ_API_KEY` needs to be added to `.env` (which currently only has `GEMINI_API_KEY`).

**Step 3 — Compare Gemini vs Qwen vs Groq:** **Cannot be done** — only Gemini output exists. Directly blocked by Steps 1 and 2 not producing artifacts.

**Step 4 — Select best approach based on evidence:** **Not done**, no evidence exists yet to select from.

**Step 5 — Create separate batch pipeline, don't overwrite `batch_extract.py`:** **Not done** — no `batch_extract_groq.py` / `batch_extract_local.py` exists. Note: `batch_extract.py` itself does have an uncommitted local modification (see Risks below) — but that diff only fixes bugs in the existing Gemini logic (e.g., the previous version had a broken `OUTPUT_FOLDER = Path(OUTPUT_FOLDER = Path(...))` self-referential assignment that would have raised `NameError`) and adds interactive batch sizing/ETA — it does not add Qwen/Groq logic, so it is not literally "overwriting batch_extract.py with the alternate approach," but it does mean the file the plan says to leave alone was actively being edited.

**Step 6/7/8 — Validate new pipeline on 5 / 20 / 100 PDFs:** **N/A**, blocked entirely by Step 5 not existing.

**Step 9 — Process all 2,066 PDFs:** **Not reached.** Only 17 processed via the Gemini path, which is itself not yet the "selected" approach per the plan's own process.

**Bottom-line blocker:** none of steps 3–9 can proceed until Step 2 (write `test_docling_groq.py`) exists and both Step 1 and Step 2 produce actual saved JSON output to compare.

---

## 6. Risks / Deviations from Rules (plan section 42)

1. **Rule 1 (don't modify production pipeline while testing experimental models) — partially at risk.** `batch_extract.py` has an uncommitted local diff (confirmed via `git diff`) made in the same working session as the new `test_docling_*` experimental files. The change is a legitimate bugfix + polish pass (fixes a broken `Path()` self-assignment, adds interactive batch sizing, adds a dedicated quota-exit branch, adds ETA), not an addition of alternate-model logic — but it is still a direct edit to the file the plan explicitly names as off-limits during this phase, and there is no test coverage (`backend/tests/` is an empty directory) to catch regressions from it.

2. **Rule 2 (don't process all 2,066 before validation) — followed.** Only 17/2,066 processed, consistent with the plan's staged-testing philosophy (even if the actual stoppage was quota exhaustion rather than a deliberate checkpoint).

3. **Rule 3 (no hardcoded API keys) — followed.** Verified via `git grep` across tracked history for common key prefixes (`sk-`, `AIza`, `gsk_`) — no matches. `.env` is not tracked.

4. **Rule 7 (don't blindly remove text based on keywords) — VIOLATED, with a reproduced live bug.** `preprocess.py`'s `REMOVE_PHRASES` list includes bare substrings like `"Eng"` and `"English"`, removed via a plain `text.replace(phrase, "")` with no word-boundary check. I reproduced this directly:

   ```
   Input:  "The Assistant Engineer (Civil) certified the plan. Applicants from England are eligible."
   Output: "The Assistant ineer (Civil) certified the plan. Applicants from land are eligible."
   ```

   This runs on every PDF processed through the Gemini pipeline (`preprocess_text` is called at `batch_extract.py:128`) before the text ever reaches the LLM — meaning any scheme document mentioning "Engineer," "England," "Bengal," or any other word containing the substring "Eng" is being silently corrupted upstream of extraction. This is exactly the failure mode Rule 7 warns against, and it is currently live in the "working" pipeline, not just a hypothetical.

5. **Encoding artifacts not actually fixed (section 6.2 / Rule 4-adjacent).** Mojibake (`â€œ`, `â‚¹`) is present verbatim in real saved output (`25-ciss copy.json`), despite being called out as a known issue. `postprocess.py` never addresses it.

6. **Environment reproducibility gap.** `backend/requirements.txt` is committed but empty (0 bytes), and the currently active `venv/` is missing `fitz`/`pymupdf` and `google-genai` — the two packages the "completed" Gemini pipeline depends on. Anyone (including a future AI/developer per section 47) who runs `pip install -r requirements.txt` today gets nothing, and running `batch_extract.py` as-is will crash on import.

7. **Untracked, un-ignored `venv_old/` sitting in the repo.** This is the broken Python-3.12 environment described in plan section 16 (confirmed: `venv_old/Scripts/python.exe` fails with `No Python at 'C:\Python312\python.exe'`). It is not in `.gitignore` and shows as untracked (`??`) in `git status` — a `git add -A` would attempt to stage an entire second Python environment.

8. **Dead configuration.** `backend/config/ui_noise_patterns.txt` (33 curated phrases, more complete than the code's own list) is never loaded by any script — wasted/orphaned work, and a likely source of confusion for whoever picks this up next.

9. **Schema drift.** The schema documented in the plan (section 7, flat structure) no longer matches the schema actually shipped in `schema.py` (nested structure). Anyone reading the plan to understand the target JSON shape will build against the wrong structure.

10. **PROJECT_PLAN.md itself is not version-controlled.** The plan document lives at `docs/Government_Scheme_AI_PROJECT_PLAN.md` and is untracked (shows under `docs/` in `git status` as a new, uncommitted directory) — the single source of truth for project direction currently has no history and could be lost or diverge silently from what collaborators see on GitHub.

---

## 7. Recommended Next 3 Actions

1. **Fix the environment before touching anything else.** Run `pip freeze > backend/requirements.txt` from an environment that actually has `pymupdf` + `google-genai` installed (or `pip install pymupdf google-genai` into the current `venv/` first), commit the real `requirements.txt`, and delete or `.gitignore` `venv_old/`. Right now the plan's own "completed" pipeline cannot run in the checked-out environment — this blocks everything else.

2. **Fix the `preprocess.py` substring-removal bug** (drop `"Eng"`/`"English"` from `REMOVE_PHRASES`, or switch all phrase removal to word-boundary regex matching, e.g. `re.sub(rf"\b{re.escape(phrase)}\b", "", text)`), then re-run it against the 17 already-processed PDFs to check how much silent corruption already exists in saved output. This is actively degrading data quality in the one pipeline that's supposedly working.

3. **Actually execute Step 1 and Step 2 of section 36** — run `test_docling_qwen.py` end-to-end and confirm `25-ciss_qwen.json` is produced, then write and run `test_docling_groq.py` (add `GROQ_API_KEY` to `.env`, reuse the Qwen script's structure against Groq's OpenAI-compatible endpoint). Without both artifacts existing, Steps 3–9 of the plan (compare, select, build batch pipeline, scale to 2,066) are structurally impossible to start.
