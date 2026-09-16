"""Phase 10 RAG evaluation: runs all 50 test queries through the full chat pipeline
and reports decline rate on out-of-scope queries, source citation rate, average
response time, and a manual retrieval spot-check on the 10 scheme-search queries.

Run: python -m chatbot.evaluation.eval_rag  (from repo root)
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from chatbot.backend.api.main import _process_message
from chatbot.backend.rag.generator import DECLINE_MESSAGE
from chatbot.backend.retrieval.retriever import retrieve

QUERIES_PATH = Path(__file__).resolve().parent / "test_queries.json"


def load_queries() -> list[dict]:
    with open(QUERIES_PATH, encoding="utf-8") as f:
        return json.load(f)


def run_full_pipeline(queries: list[dict]) -> list[dict]:
    results = []
    for q in queries:
        start = time.perf_counter()
        try:
            result = _process_message(q["query"], session_id=None, language_override=None)
            error = None
        except Exception as exc:  # noqa: BLE001 - eval script must not crash on one bad query
            result = {"answer": "", "sources": [], "confidence": "low", "intent": "error"}
            error = str(exc)
        elapsed = time.perf_counter() - start

        results.append(
            {
                "id": q["id"],
                "category": q["category"],
                "query": q["query"],
                "answer": result["answer"],
                "sources": result["sources"],
                "confidence": result["confidence"],
                "intent": result["intent"],
                "response_time_s": round(elapsed, 3),
                "error": error,
            }
        )
        print(f"[{q['id']:>2}] {q['category']:<18} intent={result['intent']:<16} "
              f"{elapsed:5.2f}s  sources={len(result['sources'])}  "
              f"{q['query'][:60]}")
    return results


def is_declined(answer: str) -> bool:
    lowered = answer.lower()
    return (
        DECLINE_MESSAGE.strip().lower() in lowered
        or "i can only help with government scheme" in lowered
        or "i can't process that message" in lowered
        or "myscheme.gov.in" in lowered
    )


def compute_metrics(results: list[dict]) -> dict:
    out_of_scope = [r for r in results if r["category"] == "out_of_scope"]
    declined = [r for r in out_of_scope if is_declined(r["answer"])]
    decline_rate = len(declined) / len(out_of_scope) * 100 if out_of_scope else 0.0

    non_error = [r for r in results if r["intent"] != "error"]
    with_sources = [r for r in non_error if len(r["sources"]) > 0]
    citation_rate = len(with_sources) / len(non_error) * 100 if non_error else 0.0

    avg_response_time = sum(r["response_time_s"] for r in results) / len(results) if results else 0.0

    return {
        "total_queries": len(results),
        "out_of_scope_total": len(out_of_scope),
        "out_of_scope_declined": len(declined),
        "decline_rate_pct": round(decline_rate, 1),
        "source_citation_rate_pct": round(citation_rate, 1),
        "avg_response_time_s": round(avg_response_time, 3),
    }


def spot_check_retrieval(queries: list[dict]) -> list[dict]:
    scheme_queries = [q for q in queries if q["category"] == "scheme_search"]
    spot_checks = []
    for q in scheme_queries:
        hits = retrieve(q["query"], top_k=5)
        top5_names = [h["scheme_name"] for h in hits]
        expected = q.get("expected_scheme", "")
        found = any(
            expected and (expected.split(" / ")[0].lower() in name.lower() or name.lower() in expected.lower())
            for name in top5_names
        )
        spot_checks.append(
            {
                "id": q["id"],
                "query": q["query"],
                "expected_scheme": expected,
                "top5_scheme_names": top5_names,
                "found_in_top5": found,
            }
        )
        marker = "OK" if found else "MISS"
        print(f"[{marker}] q{q['id']}: expected={expected!r}")
        for name in top5_names:
            print(f"        - {name}")
    return spot_checks


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    queries = load_queries()

    print("=" * 70)
    print("Running all 50 queries through the full chat pipeline...")
    print("=" * 70)
    results = run_full_pipeline(queries)

    print("\n" + "=" * 70)
    print("Manual retrieval spot-check on 10 scheme-search queries")
    print("=" * 70)
    spot_checks = spot_check_retrieval(queries)
    retrieval_hits = sum(1 for s in spot_checks if s["found_in_top5"])

    metrics = compute_metrics(results)
    metrics["retrieval_spot_check_hits"] = retrieval_hits
    metrics["retrieval_spot_check_total"] = len(spot_checks)
    metrics["retrieval_spot_check_pct"] = round(
        retrieval_hits / len(spot_checks) * 100 if spot_checks else 0.0, 1
    )

    print("\n" + "=" * 70)
    print("RAG EVALUATION SUMMARY")
    print("=" * 70)
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    out_path = Path(__file__).resolve().parent / "eval_rag_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"metrics": metrics, "results": results, "spot_checks": spot_checks}, f, indent=2, ensure_ascii=False)
    print(f"\nFull results written to {out_path}")

    return metrics


if __name__ == "__main__":
    main()
