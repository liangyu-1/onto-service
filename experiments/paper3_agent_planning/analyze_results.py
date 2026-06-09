#!/usr/bin/env python3
"""Analyze experiment results: McNemar test, violation breakdown, etc."""
from __future__ import annotations

import json
import math
import pathlib
import sys
from math import comb
from statistics import mean
from typing import Dict, List, Tuple

sys.path.insert(0, "src")


def metric_value(result: Dict, metric: str) -> bool:
    """Read a metric with backward-compatible fallbacks for old result files."""
    if metric in result:
        return bool(result.get(metric, False))
    if metric == "final_name_match":
        return result.get("predicted_final") == result.get("gold_final")
    if metric == "final_exact_match":
        pred = result.get("predicted_final_call")
        gold = result.get("gold_final_call")
        return bool(pred and gold and pred == gold)
    if metric == "strict_success":
        # Legacy files used a different success definition. Do not infer strict
        # success from them; re-run experiments to obtain this metric.
        return False
    return bool(result.get(metric, False))


def paired_by_task_id(left_results: List[Dict], right_results: List[Dict]) -> List[Tuple[Dict, Dict]]:
    """Align two planner result lists by task_id and drop errored/unpaired rows."""
    left_by_id = {
        r.get("task_id"): r
        for r in left_results
        if "error" not in r and r.get("task_id") is not None
    }
    right_by_id = {
        r.get("task_id"): r
        for r in right_results
        if "error" not in r and r.get("task_id") is not None
    }
    common_ids = sorted(set(left_by_id) & set(right_by_id), key=lambda x: str(x))
    return [(left_by_id[task_id], right_by_id[task_id]) for task_id in common_ids]


def mcnemar_test(schema_results: List[Dict], ours_results: List[Dict], metric: str = "success") -> Dict:
    """Exact McNemar test for paired binary outcomes."""
    # Contingency table:
    # b = Schema-Only fails, Ours succeeds
    # c = Schema-Only succeeds, Ours fails
    b = 0  # Ours improves
    c = 0  # Ours worsens
    
    pairs = paired_by_task_id(schema_results, ours_results)
    if not pairs:
        pairs = [
            (s, o)
            for s, o in zip(schema_results, ours_results)
            if "error" not in s and "error" not in o
        ]

    for s, o in pairs:
        s_ok = metric_value(s, metric)
        o_ok = metric_value(o, metric)
        if not s_ok and o_ok:
            b += 1
        elif s_ok and not o_ok:
            c += 1
    
    if b + c == 0:
        chi2 = 0
        p_value = 1.0
    else:
        # Report the common asymptotic statistic, but use the exact two-sided
        # binomial p-value because the discordant count can be small.
        chi2 = (b - c) ** 2 / (b + c)
        n = b + c
        k = min(b, c)
        p_value = min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / (2**n))
    
    return {
        "b_ours_improves": b,
        "c_ours_worsens": c,
        "chi2": round(chi2, 3),
        "p_value": round(p_value, 4),
        "test": "exact two-sided McNemar/binomial",
        "significant_05": p_value < 0.05,
        "significant_01": p_value < 0.01,
        "metric": metric,
        "paired_n": len(pairs),
    }


def paired_effect(schema_results: List[Dict], ours_results: List[Dict], metric: str) -> Dict:
    """Paired absolute improvement for a binary metric."""
    paired_rows = paired_by_task_id(schema_results, ours_results)
    if not paired_rows:
        paired_rows = [
            (s, o)
            for s, o in zip(schema_results, ours_results)
            if "error" not in s and "error" not in o
        ]
    pairs = [(1 if metric_value(s, metric) else 0, 1 if metric_value(o, metric) else 0) for s, o in paired_rows]
    if not pairs:
        return {"metric": metric, "schema_rate": 0, "ours_rate": 0, "delta": 0}
    schema_vals = [p[0] for p in pairs]
    ours_vals = [p[1] for p in pairs]
    deltas = [o - s for s, o in pairs]
    return {
        "metric": metric,
        "n": len(pairs),
        "schema_rate": round(mean(schema_vals), 4),
        "ours_rate": round(mean(ours_vals), 4),
        "delta": round(mean(deltas), 4),
        "delta_ci_95": paired_delta_ci(deltas),
    }


def paired_delta_ci(deltas: List[int]) -> Tuple[float, float]:
    """Approximate 95% CI for paired binary absolute improvement."""
    if not deltas:
        return (0.0, 0.0)
    n = len(deltas)
    avg = mean(deltas)
    if n == 1:
        return (round(avg, 4), round(avg, 4))
    variance = sum((d - avg) ** 2 for d in deltas) / (n - 1)
    se = math.sqrt(variance / n)
    return (round(avg - 1.96 * se, 4), round(avg + 1.96 * se, 4))


def wilson_ci(successes: int, total: int, z: float = 1.96) -> Tuple[float, float]:
    """Wilson score interval for a single binary rate."""
    if total <= 0:
        return (0.0, 0.0)
    p = successes / total
    denom = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denom
    return (round(center - margin, 4), round(center + margin, 4))


def violation_breakdown(results: List[Dict]) -> Dict:
    """Break down executed and internally rejected violations by type."""
    vtypes = {
        "DUPLICATE": 0,
        "PRECONDITION": 0,
        "CONSTRAINT": 0,
        "Unknown action": 0,
        "OTHER": 0,
    }
    
    for r in results:
        for step in r.get("step_details", []):
            for v in step.get("verifier_violations", []):
                if v.startswith("DUPLICATE"):
                    vtypes["DUPLICATE"] += 1
                elif v.startswith("PRECONDITION"):
                    vtypes["PRECONDITION"] += 1
                elif v.startswith("CONSTRAINT"):
                    vtypes["CONSTRAINT"] += 1
                elif v.startswith("Unknown action"):
                    vtypes["Unknown action"] += 1
                else:
                    vtypes["OTHER"] += 1
            for repair in step.get("repair_trace", []):
                for v in repair.get("violations", []):
                    if v.startswith("DUPLICATE"):
                        vtypes["DUPLICATE"] += 1
                    elif v.startswith("PRECONDITION"):
                        vtypes["PRECONDITION"] += 1
                    elif v.startswith("CONSTRAINT"):
                        vtypes["CONSTRAINT"] += 1
                    elif v.startswith("Unknown action"):
                        vtypes["Unknown action"] += 1
                    else:
                        vtypes["OTHER"] += 1
    
    return vtypes


def claim_readiness(data: Dict[str, List[Dict]], left: str = "Schema-Only", right: str = "Ours") -> Dict:
    """Assess whether results support the paper's main task-performance claim."""
    if left not in data or right not in data:
        return {
            "claim": f"{right} significantly improves task performance over {left}",
            "ready": False,
            "reasons": [f"Missing required planners: {left} and/or {right}"],
        }

    left_results = [r for r in data[left] if "error" not in r]
    right_results = [r for r in data[right] if "error" not in r]
    paired_rows = paired_by_task_id(left_results, right_results)
    if not paired_rows:
        return {
            "claim": f"{right} significantly improves task performance over {left}",
            "ready": False,
            "reasons": ["Planner result counts are empty or cannot be paired by task_id."],
        }

    effect = paired_effect(left_results, right_results, "success")
    sig = mcnemar_test(left_results, right_results, "success")
    paired_left = [p[0] for p in paired_rows]
    paired_right = [p[1] for p in paired_rows]
    right_success = sum(1 for r in paired_right if metric_value(r, "success"))
    left_success = sum(1 for r in paired_left if metric_value(r, "success"))
    total = len(paired_rows)
    evaluator_names = sorted(set(r.get("evaluator_name", "legacy_or_unknown") for r in paired_right))
    official_flags = [bool(r.get("official_tau_bench_available", False)) for r in paired_right]
    official_available = all(official_flags)
    uses_official_reward = all(str(r.get("evaluator_name", "")).startswith("official_tau_bench") for r in paired_right)
    coverage_warnings = sum(r.get("coverage_warning_count", 0) for r in paired_right)

    reasons = []
    if total < 40:
        reasons.append(f"Paired sample size is {total}; retail tau-bench test evaluation should use all 40 test tasks.")
    if not official_available:
        reasons.append("Official tau-bench package is not available for every paired result.")
    if not uses_official_reward:
        reasons.append("Results are not scored by an official tau-bench reward/evaluator; do not claim official tau-bench task-performance improvement.")
    if "legacy_or_unknown" in evaluator_names:
        reasons.append("Results are legacy/unknown evaluator format; rerun experiments with current code.")
    if effect["delta"] <= 0:
        reasons.append("Task success delta is not positive.")
    if not sig["significant_05"]:
        reasons.append("Task success improvement is not statistically significant at p < 0.05.")
    if coverage_warnings:
        reasons.append(f"Local evaluator emitted {coverage_warnings} coverage warnings.")

    return {
        "claim": f"{right} significantly improves task performance over {left}",
        "ready": not reasons,
        "left": left,
        "right": right,
        "n": total,
        "left_success": left_success,
        "right_success": right_success,
        "left_success_ci_95": wilson_ci(left_success, total),
        "right_success_ci_95": wilson_ci(right_success, total),
        "delta": effect["delta"],
        "delta_ci_95": effect["delta_ci_95"],
        "mcnemar": sig,
        "evaluator_names": evaluator_names,
        "official_tau_bench_available": official_available,
        "coverage_warnings": coverage_warnings,
        "reasons": reasons,
    }


def analyze_experiment(result_dir: str):
    """Analyze all results in a directory."""
    result_path = pathlib.Path(result_dir)

    if result_path.is_file():
        combined_file = result_path
    else:
        combined_files = sorted(result_path.glob("all_results_*.json"))
        if not combined_files:
            print(f"No combined results found in {result_dir}")
            return
        combined_file = combined_files[-1]

    with open(combined_file) as f:
        data = json.load(f)
    
    print("=" * 70)
    print(f"EXPERIMENT ANALYSIS: {result_dir}")
    print("=" * 70)
    any_result = next((r for rs in data.values() for r in rs if isinstance(r, dict)), {})
    if any_result and "local_reward" not in any_result:
        print("WARNING: Results use the legacy format without local_reward.")
        print("         Re-run run_experiments.py for paper-grade local DB-state metrics.")
    
    # Per-planner summary
    for planner_name, results in data.items():
        valid = [r for r in results if "error" not in r]
        if not valid:
            continue
        
        total = len(valid)
        success = sum(1 for r in valid if r.get("success", False))
        strict_success = sum(1 for r in valid if r.get("strict_success", False))
        local_db_reward = sum(1 for r in valid if r.get("local_db_reward", r.get("db_hash_match", r.get("db_state_match", False))))
        avg_acc = sum(r.get("accuracy", 0) for r in valid) / total
        avg_exact_acc = sum(r.get("exact_action_accuracy", 0) for r in valid) / total
        total_v = sum(r.get("violation_count", 0) for r in valid)
        total_rejected_v = sum(r.get("rejected_violation_count", 0) for r in valid)
        total_i = sum(r.get("invalid_count", 0) for r in valid)
        total_repairs = sum(r.get("repair_count", 0) for r in valid)
        total_grounding_changes = sum(r.get("grounding_change_count", 0) for r in valid)
        total_grounding_rejections = sum(r.get("grounding_rejection_count", 0) for r in valid)
        total_progress_rejections = sum(r.get("progress_rejection_count", 0) for r in valid)
        tasks_with_cases = sum(1 for r in valid if r.get("retrieved_case_count", 0) > 0)
        total_suggestions = sum(r.get("suggestion_count_total", 0) for r in valid)
        total_suggestion_fallbacks = sum(r.get("suggestion_fallback_count", 0) for r in valid)
        total_update_suggestion_fallbacks = sum(r.get("update_suggestion_fallback_count", 0) for r in valid)
        total_coverage_warnings = sum(r.get("coverage_warning_count", 0) for r in valid)
        evaluator_names = sorted(set(r.get("evaluator_name", "legacy_or_unknown") for r in valid))
        official_available = any(r.get("official_tau_bench_available", False) for r in valid)
        
        print(f"\n{planner_name}:")
        print(f"  Local DB Reward: {local_db_reward}/{total} = {100*local_db_reward/total:.1f}%")
        print(f"  Local DB Success Rate: {success}/{total} = {100*success/total:.1f}%")
        print(f"  Strict Success Rate: {strict_success}/{total} = {100*strict_success/total:.1f}%")
        print(f"  Avg Name-Prefix Accuracy: {avg_acc*100:.1f}%")
        print(f"  Avg Exact-Prefix Accuracy: {avg_exact_acc*100:.1f}%")
        print(f"  Executed Violations: {total_v}")
        print(f"  Rejected Violations: {total_rejected_v}")
        print(f"  Total Invalid: {total_i}")
        print(f"  Repair Attempts: {total_repairs}")
        print(f"  Grounding Changes: {total_grounding_changes}")
        print(f"  Grounding Rejections: {total_grounding_rejections}")
        print(f"  Progress Rejections: {total_progress_rejections}")
        print(f"  Tasks with Retrieved Train Cases: {tasks_with_cases}/{total}")
        print(f"  Total Suggested Actions: {total_suggestions}")
        print(f"  Suggestion Fallbacks Used: {total_suggestion_fallbacks}")
        print(f"  Update Suggestion Fallbacks Used: {total_update_suggestion_fallbacks}")
        print(f"  Evaluator: {evaluator_names} (official_tau_bench_available={official_available})")
        print(f"  Coverage Warnings: {total_coverage_warnings}")
        
        # Violation breakdown
        vtypes = violation_breakdown(valid)
        if sum(vtypes.values()) > 0:
            print(f"  Violation Breakdown:")
            for vtype, count in vtypes.items():
                if count > 0:
                    print(f"    {vtype}: {count}")
    
    # McNemar tests for available paired planners.
    planner_pairs = [
        ("Schema-Only", "OursNoCases"),
        ("Schema-Only", "Ours"),
        ("OursNoCases", "Ours"),
    ]
    available_pairs = [(a, b) for a, b in planner_pairs if a in data and b in data]
    if available_pairs:
        print("\n" + "=" * 70)
        print("PAIRED SIGNIFICANCE TESTS")
        print("=" * 70)
        for left, right in available_pairs:
            print(f"\n{left} vs {right}:")
            for metric in ("success", "strict_success", "final_exact_match", "final_name_match"):
                effect = paired_effect(data[left], data[right], metric)
                mcnemar = mcnemar_test(data[left], data[right], metric)
                print(f"\n  Metric: {metric}")
                print(f"    {left} rate: {effect['schema_rate']*100:.1f}%")
                print(f"    {right} rate: {effect['ours_rate']*100:.1f}%")
                print(f"    Absolute delta: {effect['delta']*100:.1f} pp")
                print(f"    {right} improves: {mcnemar['b_ours_improves']}")
                print(f"    {right} worsens: {mcnemar['c_ours_worsens']}")
                print(f"    Chi-square: {mcnemar['chi2']}")
                print(f"    Exact p-value: {mcnemar['p_value']}")
                print(f"    Significant (p<0.05): {mcnemar['significant_05']}")

    print("\n" + "=" * 70)
    print("CLAIM READINESS")
    print("=" * 70)
    assessment = claim_readiness(data, "Schema-Only", "Ours")
    print(f"Claim: {assessment['claim']}")
    print(f"Ready for main paper claim: {assessment['ready']}")
    if "n" in assessment:
        print(f"  n: {assessment['n']}")
        print(
            f"  Success: {assessment['left']}={assessment['left_success']} "
            f"CI95={assessment['left_success_ci_95']} | "
            f"{assessment['right']}={assessment['right_success']} "
            f"CI95={assessment['right_success_ci_95']}"
        )
        print(f"  Delta: {assessment['delta']*100:.1f} pp CI95={assessment['delta_ci_95']}")
        print(f"  McNemar p-value: {assessment['mcnemar']['p_value']}")
        print(f"  Evaluator: {assessment['evaluator_names']}")
        print(f"  Official tau-bench available: {assessment['official_tau_bench_available']}")
        print(f"  Coverage warnings: {assessment['coverage_warnings']}")
    if assessment.get("reasons"):
        print("  Blocking reasons:")
        for reason in assessment["reasons"]:
            print(f"    - {reason}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("result_dir", default="results_kimi_40", nargs="?")
    args = parser.parse_args()
    analyze_experiment(args.result_dir)
