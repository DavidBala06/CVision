"""Tests for the shortlisting evaluator (no LLM calls — uses a fake matcher)."""
import json
import tempfile
from pathlib import Path

import pytest

from evals.evaluator import _names_from_result, evaluate_case, run_evaluation


class TestNameExtraction:
    def test_list_of_dicts(self):
        result = [{"name": "Alice"}, {"name": "Bob"}]
        assert _names_from_result(result) == ["alice", "bob"]

    def test_single_dict_wrapped(self):
        result = {"name": "Alice"}
        assert _names_from_result(result) == ["alice"]

    def test_empty_returns_empty(self):
        assert _names_from_result(None) == []
        assert _names_from_result([]) == []


class TestEvaluateCase:
    def test_perfect_match(self):
        metrics = evaluate_case(
            predicted=["alice", "bob", "carol"],
            expected=["Alice", "Bob"],
            must_not_match=["Eve"],
            k=3,
        )
        assert metrics["hit"] is True
        assert metrics["precision_at_k"] == pytest.approx(2 / 3, abs=0.01)
        assert metrics["recall_at_k"] == 1.0
        assert metrics["reciprocal_rank"] == 1.0
        assert metrics["negative_leak"] is False

    def test_negative_leak_detected(self):
        metrics = evaluate_case(
            predicted=["eve"],
            expected=["Alice"],
            must_not_match=["Eve"],
            k=3,
        )
        assert metrics["negative_leak"] is True
        assert metrics["hit"] is False

    def test_mrr_decays_with_rank(self):
        first = evaluate_case(["alice", "x", "y"], ["Alice"], [], k=3)
        second = evaluate_case(["x", "alice", "y"], ["Alice"], [], k=3)
        assert first["reciprocal_rank"] == 1.0
        assert second["reciprocal_rank"] == 0.5


class TestRunEvaluation:
    def test_against_fake_matcher(self, tmp_path):
        gt = {
            "cases": [
                {
                    "id": "t1",
                    "query": "python dev",
                    "expected_candidates": ["Alice"],
                    "must_not_match": ["Eve"],
                },
                {
                    "id": "t2",
                    "query": "java dev",
                    "expected_candidates": ["Bob"],
                    "must_not_match": [],
                },
            ]
        }
        gt_path = tmp_path / "gt.json"
        gt_path.write_text(json.dumps(gt))

        # Fake matcher: returns Alice for python query, nothing for java
        def fake(query: str):
            if "python" in query.lower():
                return [{"name": "Alice"}, {"name": "Carol"}]
            return []

        result = run_evaluation(fake, k=3, ground_truth_path=gt_path, persist=False)

        agg = result["aggregated"]
        assert agg["total_cases"] == 2
        assert agg["hit_rate"] == 0.5  # one passed, one missed
        assert agg["mrr"] == 0.5      # one case at rank 1, one missed
        assert agg["negative_leak_rate"] == 0.0
