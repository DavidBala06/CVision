"""
CLI to run the shortlisting evaluation against the live matcher chain.

Usage:
    cd backend
    python -m evals.run_eval [--k 3]
"""
import argparse
import json
import logging
import sys
from pathlib import Path

# Allow running as `python -m evals.run_eval` from backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai.RAG_engine import build_vector_database, create_retriever_chain  # noqa: E402
from evals.evaluator import run_evaluation  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("eval")


def main():
    parser = argparse.ArgumentParser(description="Evaluate the shortlisting chain.")
    parser.add_argument("--k", type=int, default=3, help="Top-k cutoff")
    args = parser.parse_args()

    logger.info("Building vector DB…")
    db = build_vector_database()
    if db is None:
        logger.error("Vector DB could not be built. Did you run the migration first?")
        sys.exit(1)

    logger.info("Building matcher chain…")
    matcher = create_retriever_chain(db)
    if matcher is None:
        logger.error("Matcher chain not available.")
        sys.exit(1)

    def invoke(query: str):
        return matcher.invoke({"input": query})

    logger.info("Running evaluation (k=%d)…", args.k)
    result = run_evaluation(invoke, k=args.k)

    agg = result.get("aggregated", {})
    print()
    print("=" * 60)
    print(" SHORTLISTING EVAL RESULTS")
    print("=" * 60)
    print(f"  Cases:                  {agg.get('total_cases')}")
    print(f"  Hit rate:               {agg.get('hit_rate'):.1%}")
    print(f"  Mean Precision@{args.k}:      {agg.get('mean_precision_at_k'):.3f}")
    print(f"  Mean Recall@{args.k}:         {agg.get('mean_recall_at_k'):.3f}")
    print(f"  MRR:                    {agg.get('mrr'):.3f}")
    print(f"  Negative leak rate:     {agg.get('negative_leak_rate'):.1%}")
    print(f"  Accuracy (passing):     {agg.get('accuracy'):.1%}  (target ≥ 80%)")
    print(f"  Meets target:           {'YES' if agg.get('meets_target') else 'NO'}")
    print("=" * 60)
    print()

    fails = [c for c in result.get("per_case", []) if not c["hit"] or c["negative_leak"]]
    if fails:
        print("Failing cases:")
        for c in fails:
            print(f"  [{c['id']}] {c['query']}")
            print(f"    expected: {c['expected']}")
            print(f"    got:      {c['predicted_top_k']}")
            if c["leaks"]:
                print(f"    LEAKED:   {c['leaks']}")
        print()

    print(f"Full results written to: {Path(__file__).parent / 'last_run.json'}")


if __name__ == "__main__":
    main()
