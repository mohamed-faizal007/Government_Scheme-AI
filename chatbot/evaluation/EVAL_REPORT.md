# Phase 10 — Evaluation Report

## What each change did (summary table)

| Metric | 1. 488 schemes (2026-10-10) | 2. 2,066, before token budget | 3. + token budget (14-id subset only) | 4. + cleanup (descriptions, 73 names, router): regression | 5. + skip content-free description chunks | 6. + citation-guard fix + tighter Romanized-Hindi patterns (current) | 7. + exact-name prompt line + 2,500-character cap |
|---|---|---|---|---|---|---|---|
| Out-of-scope declined | 80% (8/10) | 100% (10/10), 2 only by request failure | 10/10; q35, q38 by the guard | 100% (10/10): 8 router, 2 guard | 100% (10/10): 8 router, 2 guard | **100% (10/10): 8 router (31-34, 36, 37, 39, 40), 2 citation guard (35, 38)** | **10/10: 8 router, 2 citation guard (35, 38)** |
| Source citation rate | 30% (15/50) | 26% (13/50) | 14.3% of the 14 ids (not comparable) | 16% (8/50) | 26% (13/50) | **28% (14/50)** | **32% (16/50)** |
| Retrieval spot-check (top 5) | 70% (7/10) | 70% (7/10) | not run | 60% (6/10), q1 misses | 70% (7/10) | **70% (7/10)** | **70% (7/10)** |
| Average response time | 28.9s | 11.2s | 1.7s (14 ids) | 2.1s | 2.5s | **3.7s** | **4.4s** (2.3s without q29, which took 110s on the Ollama fallback) |
| Groq 413 failures | n/a | 5 | 0 | 0 | 0 | **0** | **0** |
| Answers per model (log selections) | 20b + Ollama (11 queries via Ollama) | 20b 9, 120b 6, Ollama 4 | 20b only | 20b 16, 120b 7, Ollama 0 | 20b 19, 120b 4, Ollama 0 | **20b 21, 120b 3, Ollama 0** | **20b 13, 120b 10, Ollama 1** |
| Eligibility accuracy | 95% (19/20) | 95% (19/20) | n/a | 95% (19/20) | 95% (19/20) | **95% (19/20)** | **95% (19/20)** |
| MongoDB docs / Chroma chunks | 488 / 1,952 | 2,066 / 8,264 | 2,066 / 8,264 | 2,066 / 8,264 | 2,066 / 7,528 | **2,066 / 7,528** | **2,066 / 7,528** |

Column 7 (kept, committed): one added line in the generator's system prompt ("Cite each scheme using its exact name as written in the context.") and `SCHEME_CHAR_CAP` raised from 1,500 to 2,500 characters (5,500-token prompt cap and 413 retry unchanged). Raw results: `eval_rag_results.json` (column 7), `eval_rag_results_before_experiment.json` (column 6). Largest request 4,093 Groq prompt tokens (was about 1,800), so there were more 429s (24 rate-limit events against 3), and one query (q29, "What identity proof documents ...") fell to Ollama and took 110s. Per-query: q3, q22 and q24 are now answered (4 sources each), q4 and q28 are still declined at low confidence (the model itself says "no reliable information"), q44 flipped from answered to declined (typo query, wording variance). Scheme/benefit queries still without sources: q4, q5, q9 (correct, not in the dataset), q26, q28. Paris: `names_scheme("The capital of France is Paris.", ...)` is False for "Atal Pension Yojana", "Dr. B." and "E."; q35 is declined by the citation guard with 0 sources.

Column 3 is a subset because only the 14 affected ids were re-run after the token budget. Raw results: `eval_rag_results.json` (column 6), `eval_rag_results_before_guard_fix.json` (column 5), `eval_rag_results_after_cleanup.json` (column 4), `eval_rag_results_subset.json` (column 3), `eval_rag_results_before_token_budget.json` (column 2); column 1 is in git history. Run-to-run differences of a query or two are model wording variance (the same query was answered in one run and declined in the next, e.g. q3, q22).

What each change did:
- **Token budget (per-scheme 1,500-character cap, 5,500-token prompt cap, 4 -> 3 -> 2 scheme retry on 413):** removed all 413 failures (requests fell from 8,917-13,741 tokens to about 1,650-1,775) and cut the average time from 11.2s to about 2s because the slow Ollama fallbacks disappeared. Cost: the cap drops most of the facts for long schemes (Assam Arogya Nidhi Scheme: 6,949 characters of benefits/application text, 1,541 reach the prompt; amounts mentioned 11 -> 3), so some "how much / what documents" questions get a low-confidence decline (q22, q28).
- **Cleanup (pop-up text stripped from all 2,066 descriptions, 73 file-name scheme names recovered from the source PDFs):** made retrieval worse. 732 schemes ended up with an empty description, so their description chunk was just `passage: <name>.` and outranked real matches (q1: the real Atal Pension Yojana chunk was at rank #22, 0.762, behind five name-only chunks).
- **Skipping content-free description chunks (732 empty + 4 under 40 characters, 736 chunks deleted):** restored the pre-cleanup level (citation 16% -> 26%, spot-check 6/10 -> 7/10).
- **Citation-guard fix (`names_scheme()` in `rag/generator.py`) and Romanized-Hindi patterns (column 6).** The guard now compares names after lower-casing, unifying Unicode hyphens/quotes, collapsing spaces and stripping edge punctuation, and requires at least 4 characters of name; stored names are unchanged (`chatbot/backend/test_citation_guard.py`, 11 cases). `kya hai`, `batao`, `bataiye`, `ke baare mein` only count together with a scheme word (yojana, scheme, labh, subsidy, pension, ...); "aaj mausam kya hai" and "mujhe kuch batao" stay out of scope, "kisan yojana ke baare mein batao" routes to scheme search. Net effect: q10 and q30 (`Abhayakiranam Scheme-`) answered, citation 26% -> 28%.

The 8 queries that declined after the cleanup (ids 1, 4, 10, 22, 24, 25, 28, 30), and q3, now:

| id | Status in column 6 | Why |
|---|---|---|
| 1, 10, 25, 30 | answered (4 sources) | fixed by the chunk skip and the guard fix |
| 4 (Hindi, Bina Mulya) | declined | the model itself returns "no reliable information" (confidence low) although the scheme is retrieved |
| 22 (benefit amount, Assam Arogya Nidhi) | declined | low confidence; the 1,500-character cap removes most of the amounts (11 -> 3 mentions) |
| 28 (claim, Aam Aadmi Bima) | declined | low confidence; claim details sit past the cap (first mention at character 2,292 of 3,375) |
| 24 (documents, Amma Two Wheeler) | declined | guard, high confidence: the model wrote "Amma Two Wheeler Scheme" without "for Working Women"; it passes or fails from run to run on the wording |
| 3 (Romanized Hindi) | declined this run, answered earlier | guard, high confidence: "Assam Arogya Nidhi (AAN) Scheme" does not contain the stored name; passes when the model writes "Assam Arogya Nidhi Scheme" |

Also new: q6 (Tamil, Amma Two Wheeler) now has 4 sources but the answer is about the wrong scheme (Snehayanam Scheme For Mothers Of Persons With Special Needs); the guard passes it because a retrieved scheme is named. q44 ("Atal Pention Yojna") and q49 ("योजना") now get answers listing schemes.

Still open:
- **The guard's exact-name match is brittle against model abbreviations** ("Amma Two Wheeler Scheme", "(AAN)"); matching on the leading words or on token overlap would remove these false declines. Not changed.
- **The 1,500-character cap is conservative**: the worst-case request is about 2.9k estimated tokens against a 5.5k budget; raising the cap to about 3,000 characters would keep the facts for long schemes while staying under the budget. Not changed.
- Tamil specific-scheme queries (q5, q6, q18, q26) still miss; recovering the 73 names did not help them, and q6 now answers with a wrong scheme.
- 13 truncated scheme names remain (`Dr. B.`, `E.`, `'`, `H.`, `J.`, `Meit`, `MMKY-`, ...), recoverable from the source PDFs like the 73; 18 descriptions of 40-80 characters are truncated sentences.
- 67 benefits/eligibility/application chunks are content-free (`passage: <name> benefits: ` alone); only description chunks were skipped.
- The pop-up sentence remains inside 84 application/eligibility/benefits chunks.

Fixed in this round: the citation guard rejecting correct answers for names with stray trailing punctuation (e.g. `Abhayakiranam Scheme-`), and Romanized-Hindi `kya hai` / `batao` routing non-scheme questions to the generator.

## Run 2026-10-21 — full corpus (2,066 schemes)

Data: 2,066 schemes in MongoDB, 8,264 chunks in ChromaDB (extraction 2,066/2,066, 0 failed, 0 schema-invalid). Embeddings: `multilingual-e5-small`.
LLM: Groq `openai/gpt-oss-20b` primary, `openai/gpt-oss-120b` fallback, Ollama `gemma3:4b` last resort. The free tier (8,000 tokens/min per model) was rate-limited throughout: the run log shows 21 rate-limit events on 20b, 15 on 120b, 10 rounds with both exhausted, 5 falls to Ollama and 5 `context_too_large` (413) events. By the log's model-selection lines, 20b was chosen 9 times, 120b 6 and Ollama 4 (counts of selections, not of answers).

Command: `python -m chatbot.evaluation.eval_rag --pause 3` (all 50 queries) and `python chatbot/evaluation/eval_eligibility.py`.

**These are the "before token budget" numbers.** The token-budget change and the subset re-run are in the next section; this table is kept unchanged.

| Metric | 2026-10-21, before token budget (2,066 schemes) | 2026-10-10 (488 schemes, history) | 2026-10-13 (488 schemes, history) |
|---|---|---|---|
| Out-of-scope decline rate | **100% (10/10)** | 80% (8/10) | 100% (10/10), ids 31-40 re-run |
| Source citation rate | **26% (13/50)** | 30% (15/50) | not re-run |
| Average response time | **11.2s** | 28.9s | not re-run |
| Retrieval spot-check (top 5) | **70% (7/10)** | 70% (7/10) | not re-run |
| Eligibility accuracy | **95% (19/20)** | 95% (19/20) | 95% (19/20) |

Findings:
- **The 100% decline rate is partly an artifact.** Queries 35 ("capital of France") and 38 (Tamil cricket) reached the generator and were declined only because Groq returned 413 and all fallbacks failed ("LLM generation failed after all fallbacks"), not because the citation guard fired. The other eight out-of-scope queries were declined by the intent router.
- **Oversized prompts on the full corpus.** Five requests exceeded the 8,000 tokens/min cap by themselves (8,917 and 13,741 tokens requested in two logged examples). A 413 cannot be fixed by retrying or switching Groq model. Queries 8, 21, 35, 38 and 49 returned a failure/"no reliable information" answer with 0 sources. Retrieved context needs a token budget.
- **Citation rate is 26%** (13/50), down from 30%. Most of the 50 queries never reach retrieval (intent router short-circuits), and the 413 failures above and the Ollama timeouts remove several more. Treat as a floor, not a clean measurement.
- **Junk scheme names in the new data.** 73 of 2,066 schemes have a `scheme_name` that is the file name (e.g. `affdf copy`, `faaadp copy`). For the Tamil queries q5 and q6 the top-5 retrieval is made of these. Spot-check misses are the same three as before (q5, q6, and q9, whose expected scheme is not in the dataset).
- **Id 3 is a router gap, not a regression:** "Assam Arogya Nidhi Scheme ke baare mein bataiye" (Romanized Hindi) matches no pattern in the keyword classifier, so it is `out_of_scope` with 0 sources. The 2026-10-10 run had the same result.
- **Eligibility** is unchanged at 95% (19/20); the single failure is still the merged multi-clause Airavata condition (SC + Karnataka + age 25), see the Eligibility section below.
- **Speed:** average 11.2s versus 28.9s, because far fewer calls waited on Ollama (4 selections versus 11 queries before). The slowest queries were still 75-130s (q6, q9, q23, q26, q30) when they fell to Ollama.

### After token budget (2026-10-21, subset re-run of the 14 affected ids)

Change (`rag/generator.py`, `llm/groq_provider.py`): each retrieved scheme's text is capped at 1,500 characters (description 500, benefits 400, eligibility 350, application 250 guaranteed, leftovers flow to later sections and the FAQ), the whole prompt is capped at about 5,500 estimated tokens, and a 413 (or a 429 that says "Request too large") retries with fewer schemes (all retrieved -> 3 -> 2) before anything falls to Ollama. Retrieval returns 4, so the ladder here is 4 -> 3 -> 2. A fake-LLM test confirmed the ladder (5 -> 3 -> 2, then the "unable to process" message).

Command: `eval_rag --ids 3,8,21,31,32,33,34,35,36,37,38,39,40,49 --pause 5` (results in `eval_rag_results_subset.json`; the full results file was not touched). No 429 and no 413 occurred in this run, and every LLM call was answered by `gpt-oss-20b`.

| id | before | after: schemes used / est. tokens / Groq prompt_tokens | model | sources | citation guard |
|---|---|---|---|---|---|
| 8 | 413, 0 sources, failure message | 4 / 2,735 / 1,774 | gpt-oss-20b | 4 | ran, passed |
| 21 | 413, 0 sources, failure message | 4 / 2,677 / 1,773 | gpt-oss-20b | 4 | ran, passed |
| 35 "capital of France" | 413 failure message | 4 / 2,658 / 1,750 | gpt-oss-20b | 0 | ran, **declined** |
| 38 Tamil cricket | 413 failure message | 4 / 2,661 / 1,649 | gpt-oss-20b | 0 | ran, **declined** |
| 49 "योजना" | 413 failure message | 4 / 2,661 / 1,719 | gpt-oss-20b | 0 | ran, declined (no scheme named) |
| 3 | router `out_of_scope` | not sent to the LLM | - | 0 | did not run |
| 31-34, 36, 37, 39, 40 | router `out_of_scope` | not sent to the LLM | - | 0 | did not run |

- **q35 and q38 are now declined by the citation guard, not by the intent router.** The router sends both to `scheme_search`; the LLM answered, the answer named no retrieved scheme, and the guard replaced it with the decline message. Before the token budget they were declined only because the request failed. All 10 out-of-scope ids are declined: 8 by the router, 2 by the guard.
- **Requests dropped from 8,917-13,741 tokens to about 1,650-1,775**, so the 8,000 tokens/min cap is no longer hit by a single query. The ladder itself did not need to fire in this run.
- The subset citation rate (14.3%) is not comparable to the full-run 26%; only q8 and q21 are scheme questions. A full 50-query re-run has not been done after the token budget.
- Not fixed: q3 ("ke baare mein", Romanized Hindi) has no router pattern and stays `out_of_scope`.

The sections below are the previous 488-scheme results, kept as history.

---

## History — 488-scheme runs (2026-10-10 and 2026-10-13)

Run date: 2026-10-10 (re-run after intent-classifier and engine fixes; supersedes the 2026-09-15 run)
LLM: Groq `openai/gpt-oss-20b` (primary) with `openai/gpt-oss-120b` as the 429 fallback (added 2026-10-13). Embeddings: `multilingual-e5-small`.

Raw outputs: `eval_rag_results.json`, `eval_eligibility_results.json`.

## Update 2026-10-13 (after citation guard, fallback chain, URL protection)

Models behind these numbers: **`openai/gpt-oss-20b` primary, `openai/gpt-oss-120b` fallback** on Groq 429. No answer in these runs came from Ollama, except the one failure noted below.

| Metric | 2026-10-10 | 2026-10-13 |
|---|---|---|
| Out-of-scope decline rate (ids 31-40) | 80% (8/10) | **100% (10/10)** |
| Eligibility accuracy | 95% (19/20) | **95% (19/20)**, unchanged |

- **Decline rate is 10/10 after the citation guard.** The generator now declines whenever an answer names none of the retrieved scheme names, at any reported confidence (the old guard only fired on `high`; the "Paris" answer was `medium`). Only queries 35 and 38 reach the generator; the other eight are declined by the intent router. An interim run printed 90% because the Tamil decline text (query 38) was not recognised by `is_declined` after translation; the URL-protection fix below preserves `myscheme.gov.in` in translated declines, so the eval now prints 100%.
- **Score threshold rejected.** Top retrieval scores: out-of-scope 0.551-0.668, English in-scope 0.714-0.835, Hindi/Tamil in-scope 0.588-0.702. Non-English in-scope queries overlap the out-of-scope range, so no similarity cutoff was used.
- **Groq fallback chain.** On a 429 the provider switches immediately to `gpt-oss-120b` (separate token bucket) instead of sleeping; the Groq SDK's own 30s+ retry is disabled so the switch is instant. Order: 20b -> 120b -> backoff rounds -> Ollama. Retrieval is now `top_k=4` (was 5) to cut tokens per request; answers stayed `high` confidence with cited sources.
- **Back-to-back test (4 queries, no pause):** farmers 8.7s (20b), 25% subsidy docs 4.3s (120b after one 429), students 3.9s (20b), Hindi farmers 137s and failed. Earlier single-model times were 34.9s, 10.7s and 54.1s for the first three. The Hindi failure is the token budget: four heavy queries in under a minute exceed two 8,000 tokens/min buckets, backoff (2s+4s) is too short to refill, and the Ollama fallback then timed out (the then-configured `qwen2.5:3b` was not installed; `.env` now points to the installed `gemma3:4b`). The same Hindi query alone took 21s with no 429s.
- **Translated declines.** `myscheme.gov.in` is now kept out of translation, so the Tamil/Hindi decline text keeps a correct URL. Tamil wording is still rough (e.g. "MyScheme" becomes "MSchem").

## Results of the 2026-10-10 run (historical; the decline-rate leak below is fixed, see above)

Setup: Groq `openai/gpt-oss-20b` primary; 11 of the LLM-bound queries exhausted Groq's rate-limit retries (45 HTTP 429 responses logged) and were answered by the Ollama fallback instead, so some answers come from a different model. This also inflates response time. Embeddings: `multilingual-e5-small`. Data: 488 schemes (MongoDB), 1,952 chunks (ChromaDB). Fixes since the 09-15 run: native Hindi/Tamil intent classification, empty-number guards in the income parsing (classifier and rules engine).

### RAG (50 queries)

| Metric | 2026-09-15 | 2026-10-10 |
|---|---|---|
| Out-of-scope decline rate | 100% (10/10) | **80%** (8/10) |
| Source citation rate | 10% (5/50) | **30%** (15/50) |
| Average response time | 4.73s | **28.9s** (429 retries + Ollama fallback) |
| Retrieval spot-check (top 5) | 70% (7/10) | **70%** (7/10) |
| Queries answered with the fallback decline message | n/a | 4 (ids 5, 6, 18, 26 — all Tamil) |
| Pipeline errors | 0 | **0** (query 12 float error fixed) |

Findings:
- **Decline rate dropped to 80% — a real leak, not noise (fixed 2026-10-13, now 10/10).** Query 35 ("What is the capital of France?") is routed to `scheme_search` by the `what is` pattern and, now that retrieval works, the LLM answered "The capital of France is Paris." Query 38 (Tamil cricket question) is also routed to `scheme_search` and got a rambling non-decline answer. The 09-15 grounding-check safety net no longer catches these; the generator needs a stricter "answer only from retrieved context" guard.
- **Tamil scheme queries still fail** (ids 5, 6, 18, 26 return the fallback). The classifier fix routes them to the right intent, but retrieval/generation for Tamil text does not find the scheme.
- **Retrieval spot-check misses** are unchanged: q5 and q6 (Tamil), q9 (Hindi PM-Kisan, scheme not in the 488-doc dataset).
- Response time is dominated by Groq rate limiting; a 3s pause and `--ids` flag were added to `eval_rag.py` for future runs.

### Eligibility engine (20 cases)

| Metric | 2026-09-15 | 2026-10-10 |
|---|---|---|
| Accuracy | 85% (17/20) | **95%** (19/20) |
| Cases with unverifiable conditions | 100% | 100% |

Remaining failure: "SC category, Karnataka, age 25 -> eligible for Airavata Scheme" returns not-eligible. The extracted condition is a single merged numbered paragraph (SC + Karnataka + other clauses); one sub-clause fails and the whole string is judged failed. Same root cause as finding 1 below.

---

## Known Limitations

- **Groq free tier: 8,000 tokens/min per model** (1,000 requests/day). A RAG request uses roughly 4-5k tokens, so about two queries per minute per model. The 20b -> 120b fallback doubles this; sustained bursts still fail over to Ollama, which is currently misconfigured (see above).
- Tamil specific-scheme name queries: retrieval fails because multilingual-e5-small does not embed specific Tamil scheme names accurately. Broad category queries (schemes for farmers, women's schemes) work correctly. Tamil uses Helsinki-NLP opus-mt-dra-en / opus-mt-en-dra; specific-scheme-name queries still miss because the model garbles proper nouns; IndicTrans2 or NLLB-200 would be an upgrade, not a blocker.

# Previous run (2026-09-15, historical)

Dataset state: 488/2,066 scheme PDFs processed and loaded (MongoDB: 488 docs, ChromaDB: 1,952 chunks).
LLM: Groq `openai/gpt-oss-20b`. Embeddings: `multilingual-e5-small`.

Raw outputs: `eval_rag_results.json`, `eval_eligibility_results.json` (generated by the scripts in this folder).

## RAG Evaluation (50 queries)

| Metric | Result |
|---|---|
| Decline rate on out-of-scope queries | **100%** (10/10 correctly declined, 0 hallucinated) |
| Source citation rate | **10%** (5/50 answers carried at least one source) |
| Average response time | **4.73s** per query |
| Retrieval spot-check (10 scheme-search queries, correct scheme in top 5) | **70%** (7/10) |

### What the numbers mean

- **Decline rate (100%)**: every out-of-scope query (weather, jokes, "capital of France", stock market, cricket scores, cooking, poetry, etc.) was declined rather than answered — no hallucinated scheme content. This holds even in the one case where the intent router itself misclassified an out-of-scope query as `scheme_search` (see below) — the RAG generator's own grounding check ("if no matching scheme content, decline") caught it as a second line of defense.
- **Source citation rate (10%) is low largely because most queries never reached the RAG generator at all.** Response time and citation numbers are dominated by intent-routing outcomes, not RAG quality per se — see the intent-router finding below, which is the real story of this run.
- **Average response time (4.73s)** is skewed by the ~5 queries that actually hit the Groq LLM (30–55s each, several rate-limited with automatic retry/backoff) against ~45 queries that short-circuited at 0.00–0.3s (out-of-scope decline, no LLM call). This is expected pipeline behavior, not a latency bug.
- **Retrieval accuracy (70%)**: 3 of 10 misses were genuine ranking misses (Airavata Scheme, Amma Two Wheeler Scheme for Working Women, and a PM-Kisan query for a scheme not yet in the 488-doc dataset — expected, since that scheme hasn't been ingested yet). The multilingual-e5 embedder pulled semantically related but wrong schemes to the top for these two real misses; investigate whether short scheme-name-only queries need a lexical/BM25 boost alongside the dense vector search.

### Real finding: intent router has a coverage gap, not a translation gap

6 of the 50 queries were misrouted to `out_of_scope` by `chatbot/backend/router/intent_classifier.py`, including real scheme-search and eligibility queries and both Tamil scheme-search queries. Root cause, verified by reading the classifier: it is a **whole-phrase English regex matcher** (`what is`, `tell me about`, `schemes for`, `am i eligible`, etc.) with no Tamil/Hindi patterns and no fallback for phrasing outside its fixed phrase list. This is a routing gap, not a translation gap — translation of the query happens correctly (log-verified), but the *translated* English text still doesn't contain any of the classifier's fixed English trigger phrases when the original phrasing was, e.g., "Explain the Airavata Scheme..." or "Which scheme helps...".

Concretely:
- Both Tamil scheme-search queries (q5, q6) → misrouted to `out_of_scope`.
- 2 English scheme-search queries phrased as "Explain the..." / "What benefits does..." / "Which scheme helps..." → misrouted.
- 1 Hindi eligibility query and 1 Tamil eligibility query → misrouted.
- Conversely, "What is the capital of France?" (genuinely out-of-scope) matched the `what is` pattern and was routed to `scheme_search` — a false positive in the other direction, only caught by the RAG generator's grounding check.

This is the single most actionable finding from this evaluation: the keyword router needs either a broader phrase list per language or a lightweight fallback classifier (e.g., embedding-similarity intent match) before Phase 11 scale-up, since it currently silently reroutes legitimate in-scope questions to the "sorry, can't help" path whenever phrasing doesn't match its fixed English templates.

## Eligibility Engine (20 test cases)

| Metric | Result |
|---|---|
| Accuracy | **85%** (17/20 correct) |
| Cases with ≥1 unverifiable condition | **100%** (20/20 — expected; see below) |

Test cases used real schemes from `dataset/gov_myscheme/test_output_unstructured/`: Assam Arogya Nidhi Scheme, Agri-Clinics and Agri-Business Centres Scheme, Accidental Death Assistance for Construction Workers (Delhi), Advance/High Skill Training (Puducherry), Airavata Scheme (Karnataka), Amma Two Wheeler Scheme for Working Women (Tamil Nadu), Abhayakiranam Scheme (Kerala), Annual Tour to the Differently Abled Persons (Puducherry), Bina Mulya Samajik Suraksha Yojana (West Bengal), Alpasankhyak Post-Maitrik Chhaatravrtti Yojana (Madhya Pradesh).

"Unverifiable conditions" appearing in all 20 cases is expected and healthy — every real scheme's condition list includes at least one clause the deterministic engine correctly refuses to guess on (e.g. educational-qualification text, BPL-card requirements, "no age limit" phrasing) rather than silently passing or failing it. That is the intended fail-safe behavior described in Phase 5 (never guess).

### Real findings: 2 genuine engine bugs (not test-case artifacts)

1. **Multi-condition strings only get evaluated on one attribute.** When the PDF extraction pipeline merges several distinct eligibility clauses into a single condition string (seen in Airavata Scheme, where age/state/category/income were all extracted as one numbered paragraph), `_evaluate()` in `rules_engine.py` checks age → income → category → state in that fixed order and **returns on the first match**, so a string containing both an age clause and a category clause is only ever evaluated on age. Test case: an OBC applicant (should fail the "Scheduled Caste" requirement) was returned as `eligible=True` because the age clause in the same string passed and the category clause was never reached.
2. **The age regex fires on unrelated "aged above N years" phrasing inside preference/priority notes, not just eligibility requirements.** In the Amma Two Wheeler Scheme, a note about *priority* being given to "Unmarried women aged above 35 years" (among other priority groups) caused a 30-year-old, otherwise-eligible applicant to be incorrectly failed, because `_check_age` pattern-matches "above 35 years" anywhere in the condition text regardless of whether that number is describing an actual eligibility threshold.

Both are pre-existing limitations of the regex-based `_evaluate()`/`_check_age` logic in `chatbot/backend/eligibility/rules_engine.py` — not introduced by this evaluation, just surfaced by it. Flagging for a future fix; no code changes made as part of Phase 10 per the evaluation-only scope.

## What to quote in interviews (from these real runs)

- "Out-of-scope decline rate is 100% across 10 adversarial off-topic queries — even when the intent router misclassifies a query, the RAG generator's own grounding check catches it as a second line of defense against hallucination."
- "The deterministic eligibility engine hit 85% accuracy on 20 hand-verified cases against real scheme data, and running the eval surfaced two concrete, reproducible bugs in how it parses multi-clause condition strings — exactly the kind of regression the eval suite is meant to catch before scaling to the full 2,066-scheme dataset."
- "Retrieval spot-checks show the multilingual embedder finds the right scheme 70% of the time in the top 5 on scheme-name queries; the 3 misses point at adding a lexical/exact-name matching layer alongside the dense vector search."
