"""
Shortlisting Evaluator — Module 4 success metrics.

Computes real accuracy metrics against ground_truth.json:
  - Precision@k       (how many of top-k are correct)
  - Recall@k          (how many expected were retrieved)
  - MRR (Mean Reciprocal Rank)
  - Hit Rate          (did at least 1 expected appear in top-k?)
  - Negative Leak     (did any must_not_match appear?)

LangChain-compatible: the matcher is invoked the same way as in production,
so the same chain is evaluated end-to-end.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from statistics import mean
from typing import Any, Callable

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
GROUND_TRUTH_PATH = BASE_DIR / "ground_truth.json"
RESULTS_PATH = BASE_DIR / "last_run.json"


def _normalize(name: str) -> str:
    return (name or "").strip().lower()


def _names_from_result(result: Any) -> list[str]:
    """Extract a list of candidate names from a matcher response."""
    if not result:
        return []
    if isinstance(result, dict):
        return [_normalize(result.get("name", ""))]
    if isinstance(result, list):
        return [_normalize(item.get("name", "")) for item in result if isinstance(item, dict)]
    return []


def evaluate_case(predicted: list[str], expected: list[str], must_not_match: list[str], k: int) -> dict:
    """Evaluate a single ground-truth case."""
    predicted_k = predicted[:k]
    expected_norm = {_normalize(n) for n in expected}
    must_not_norm = {_normalize(n) for n in must_not_match}

    hits = [n for n in predicted_k if n in expected_norm]
    leaks = [n for n in predicted_k if n in must_not_norm]

    precision = len(hits) / max(len(predicted_k), 1)
    recall = len(hits) / max(len(expected_norm), 1)

    reciprocal_rank = 0.0
    for idx, name in enumerate(predicted_k, start=1):
        if name in expected_norm:
            reciprocal_rank = 1.0 / idx
            break

    return {
        "predicted_top_k": predicted_k,
        "hits": hits,
        "leaks": leaks,
        "precision_at_k": round(precision, 3),
        "recall_at_k": round(recall, 3),
        "reciprocal_rank": round(reciprocal_rank, 3),
        "hit": len(hits) > 0,
        "negative_leak": len(leaks) > 0,
    }


def run_evaluation(
    matcher_invoke: Callable[[str], Any],
    k: int = 3,
    ground_truth_path: Path | None = None,
    persist: bool = True,
) -> dict:
    """
    Run evaluation against ground_truth.json.

    Args:
      matcher_invoke: callable(query) -> list[dict] (the RAG chain or wrapper)
      k: top-k cutoff
      ground_truth_path: optional override
      persist: write results to last_run.json

    Returns aggregated metrics + per-case detail.
    """
    path = ground_truth_path or GROUND_TRUTH_PATH
    if not path.exists():
        return {"error": f"Ground truth not found at {path}", "ran": False}

    with open(path, "r", encoding="utf-8") as f:
        gt = json.load(f)

    cases = gt.get("cases", [])
    if not cases:
        return {"error": "No cases in ground truth", "ran": False}

    per_case = []
    for case in cases:
        query = case["query"]
        try:
            result = matcher_invoke(query)
            predicted = _names_from_result(result)
        except Exception as e:
            logger.warning("Matcher error on case %s: %s", case.get("id"), e)
            predicted = []

        case_metrics = evaluate_case(
            predicted=predicted,
            expected=case.get("expected_candidates", []),
            must_not_match=case.get("must_not_match", []),
            k=k,
        )
        per_case.append({
            "id": case.get("id"),
            "query": query,
            "expected": case.get("expected_candidates", []),
            **case_metrics,
        })

    # Aggregate
    total = len(per_case)
    aggregated = {
        "k": k,
        "total_cases": total,
        "hit_rate": round(sum(1 for c in per_case if c["hit"]) / max(total, 1), 3),
        "mean_precision_at_k": round(mean(c["precision_at_k"] for c in per_case), 3),
        "mean_recall_at_k": round(mean(c["recall_at_k"] for c in per_case), 3),
        "mrr": round(mean(c["reciprocal_rank"] for c in per_case), 3),
        "negative_leak_rate": round(sum(1 for c in per_case if c["negative_leak"]) / max(total, 1), 3),
        "passing_cases": sum(1 for c in per_case if c["hit"] and not c["negative_leak"]),
    }

    aggregated["accuracy"] = round(aggregated["passing_cases"] / max(total, 1), 3)
    aggregated["target_accuracy"] = 0.80
    aggregated["meets_target"] = aggregated["accuracy"] >= 0.80

    payload = {
        "aggregated": aggregated,
        "per_case": per_case,
        "framework": "Custom LangChain-compatible evaluator (precision@k / recall@k / MRR / hit-rate)",
    }

    if persist:
        from datetime import datetime
        payload["run_at"] = datetime.utcnow().isoformat() + "Z"
        with open(RESULTS_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    return payload


def load_last_run() -> dict | None:
    """Load the most recent eval result, if any."""
    if not RESULTS_PATH.exists():
        return None
    try:
        with open(RESULTS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
