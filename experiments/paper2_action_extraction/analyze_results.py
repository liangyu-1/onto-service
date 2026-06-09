#!/usr/bin/env python3
"""Statistical analysis for paper2 results."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any, Dict, List

from scipy import stats


def mcnemar_test(
    method_a_success: List[bool],
    method_b_success: List[bool],
) -> Dict[str, Any]:
    """McNemar exact binomial test for paired binary outcomes."""
    # Contingency table:
    #          B correct | B incorrect
    # A correct    n00    |    n01
    # A incorrect  n10    |    n11
    n01 = sum(1 for a, b in zip(method_a_success, method_b_success) if a and not b)
    n10 = sum(1 for a, b in zip(method_a_success, method_b_success) if not a and b)

    if n01 + n10 == 0:
        return {"p_value": 1.0, "n01": n01, "n10": n10, "significant": False}

    # Exact binomial test
    p_value = stats.binom_test(min(n01, n10), n01 + n10, p=0.5)

    return {
        "p_value": float(p_value),
        "n01": n01,
        "n10": n10,
        "significant": p_value < 0.05,
    }


def paired_improvement(
    method_a_scores: List[float],
    method_b_scores: List[float],
) -> Dict[str, Any]:
    """Paired absolute improvement with 95% CI."""
    diffs = [b - a for a, b in zip(method_a_scores, method_b_scores)]
    mean_diff = sum(diffs) / len(diffs) if diffs else 0.0

    if len(diffs) > 1:
        sem = stats.sem(diffs)
        ci_low, ci_high = stats.t.interval(0.95, len(diffs) - 1, loc=mean_diff, scale=sem)
    else:
        ci_low, ci_high = mean_diff, mean_diff

    return {
        "mean_diff": mean_diff,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "diffs": diffs,
    }


def analyze(combined_path: pathlib.Path) -> Dict[str, Any]:
    """Analyze combined results."""
    with open(combined_path) as f:
        data = json.load(f)

    evaluations = data.get("evaluations", {})
    methods = list(evaluations.keys())

    if len(methods) < 2:
        print("Need at least 2 methods for comparison")
        return {}

    # Use a baseline metric for comparison: action_mention_f1
    baseline = methods[0]
    comparison = methods[-1]  # Usually "Ours"

    baseline_eval = evaluations[baseline]
    comparison_eval = evaluations[comparison]

    # Per-doc success (action_mention_f1 > 0.5)
    baseline_success = [v > 0.5 for v in baseline_eval.get("action_mention_f1_values", [])]
    comparison_success = [v > 0.5 for v in comparison_eval.get("action_mention_f1_values", [])]

    mcnemar = mcnemar_test(baseline_success, comparison_success)

    # Paired improvement on action_mention_f1
    baseline_f1 = baseline_eval.get("action_mention_f1_values", [])
    comparison_f1 = comparison_eval.get("action_mention_f1_values", [])
    improvement = paired_improvement(baseline_f1, comparison_f1)

    analysis = {
        "baseline": baseline,
        "comparison": comparison,
        "mcnemar": mcnemar,
        "paired_improvement": improvement,
        "claim_readiness": {
            "sample_size_ok": len(baseline_success) >= 10,
            "positive_delta": improvement["mean_diff"] > 0,
            "significant": mcnemar["significant"],
            "ready_for_paper": (
                len(baseline_success) >= 10
                and improvement["mean_diff"] > 0
                and mcnemar["significant"]
            ),
        },
    }

    return analysis


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("results_dir", type=pathlib.Path, help="Directory with combined_results.json")
    parser.add_argument("--out", type=pathlib.Path, help="Output analysis JSON")
    args = parser.parse_args()

    combined_path = args.results_dir / "combined_results.json"
    if not combined_path.exists():
        print(f"No combined_results.json found in {args.results_dir}")
        sys.exit(1)

    analysis = analyze(combined_path)

    print("\n" + "="*60)
    print("STATISTICAL ANALYSIS")
    print("="*60)
    print(f"Baseline:    {analysis['baseline']}")
    print(f"Comparison:  {analysis['comparison']}")
    print(f"McNemar p:   {analysis['mcnemar']['p_value']:.4f}")
    print(f"  n01 (baseline correct, comparison wrong): {analysis['mcnemar']['n01']}")
    print(f"  n10 (baseline wrong, comparison correct): {analysis['mcnemar']['n10']}")
    print(f"Mean Δ F1:   {analysis['paired_improvement']['mean_diff']:+.3f}")
    print(f"  95% CI:    [{analysis['paired_improvement']['ci_low']:+.3f}, {analysis['paired_improvement']['ci_high']:+.3f}]")
    print(f"Claim ready: {analysis['claim_readiness']['ready_for_paper']}")
    print("="*60)

    if args.out:
        with open(args.out, "w") as f:
            json.dump(analysis, f, indent=2)
        print(f"Analysis saved → {args.out}")


if __name__ == "__main__":
    main()
