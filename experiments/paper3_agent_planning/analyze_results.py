#!/usr/bin/env python3
"""Analyze experiment results: McNemar test, violation breakdown, etc."""
from __future__ import annotations

import json
import math
import pathlib
import sys
from collections import defaultdict
from math import comb
from statistics import mean
from typing import Dict, List, Tuple

sys.path.insert(0, "src")


def metric_value(result: Dict, metric: str) -> bool:
    """Read a metric with backward-compatible fallbacks for old result files."""
    if metric == "paper_task_performance":
        if "official_success" in result:
            return bool(result.get("official_success", False))
        if str(result.get("evaluator_name", "")).startswith(("official_tau_bench", "official_tau2")):
            return bool(result.get("success", False))
        return False
    if metric == "local_db_reward":
        return bool(result.get("local_db_reward", result.get("db_hash_match", result.get("db_state_match", False))))
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


def is_official_result(result: Dict) -> bool:
    return str(result.get("evaluator_name", "")).startswith(("official_tau_bench", "official_tau2"))


def pairing_key(result: Dict) -> str | None:
    """Return stable key for paired tests.

    Official tau2 imports may contain repeated trials for the same task. In
    that case pair_id should be task_id plus trial id. Legacy local results only
    have task_id, so we keep task_id as the fallback.
    """
    value = result.get("pair_id") or result.get("simulation_id") or result.get("task_id")
    return str(value) if value is not None else None


def task_key(result: Dict) -> str | None:
    value = result.get("task_id")
    return str(value) if value is not None else None


def paired_by_task_id(left_results: List[Dict], right_results: List[Dict]) -> List[Tuple[Dict, Dict]]:
    """Align two planner result lists by pair_id/task_id and drop errored rows."""
    left_by_id = {
        pairing_key(r): r
        for r in left_results
        if "error" not in r and pairing_key(r) is not None
    }
    right_by_id = {
        pairing_key(r): r
        for r in right_results
        if "error" not in r and pairing_key(r) is not None
    }
    common_ids = sorted(set(left_by_id) & set(right_by_id), key=lambda x: str(x))
    return [(left_by_id[task_id], right_by_id[task_id]) for task_id in common_ids]


def pair_coverage(left_results: List[Dict], right_results: List[Dict]) -> Dict:
    left_keys = {
        pairing_key(r)
        for r in left_results
        if "error" not in r and pairing_key(r) is not None
    }
    right_keys = {
        pairing_key(r)
        for r in right_results
        if "error" not in r and pairing_key(r) is not None
    }
    common = left_keys & right_keys
    left_only = sorted(left_keys - common, key=str)
    right_only = sorted(right_keys - common, key=str)
    return {
        "left_n": len(left_keys),
        "right_n": len(right_keys),
        "paired_n": len(common),
        "left_unpaired_n": len(left_only),
        "right_unpaired_n": len(right_only),
        "left_unpaired_examples": left_only[:10],
        "right_unpaired_examples": right_only[:10],
    }


def paired_task_clusters(left_results: List[Dict], right_results: List[Dict], metric: str) -> List[Dict]:
    """Aggregate paired simulations to task-level paired outcomes.

    Multiple trials on the same tau-bench task are repeated measurements of the
    same task, not independent tasks. This function first pairs by simulation
    key, then averages outcomes within each task.
    """
    by_task: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
    for left_row, right_row in paired_by_task_id(left_results, right_results):
        key = task_key(right_row) or task_key(left_row)
        if key is None:
            continue
        left_value = 1 if metric_value(left_row, metric) else 0
        right_value = 1 if metric_value(right_row, metric) else 0
        by_task[key].append((left_value, right_value))

    clusters: List[Dict] = []
    for key in sorted(by_task, key=str):
        pairs = by_task[key]
        left_rate = mean(left for left, _ in pairs)
        right_rate = mean(right for _, right in pairs)
        clusters.append({
            "task_id": key,
            "n_trials": len(pairs),
            "left_rate": left_rate,
            "right_rate": right_rate,
            "delta": right_rate - left_rate,
        })
    return clusters


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


def task_cluster_effect(left_results: List[Dict], right_results: List[Dict], metric: str) -> Dict:
    clusters = paired_task_clusters(left_results, right_results, metric)
    if not clusters:
        return {
            "metric": metric,
            "n_tasks": 0,
            "left_rate": 0,
            "right_rate": 0,
            "delta": 0,
            "delta_ci_95": (0.0, 0.0),
            "sign_test": {
                "positive_tasks": 0,
                "negative_tasks": 0,
                "zero_delta_tasks": 0,
                "p_value": 1.0,
                "significant_05": False,
            },
        }
    left_rates = [c["left_rate"] for c in clusters]
    right_rates = [c["right_rate"] for c in clusters]
    deltas = [c["delta"] for c in clusters]
    return {
        "metric": metric,
        "n_tasks": len(clusters),
        "left_rate": round(mean(left_rates), 4),
        "right_rate": round(mean(right_rates), 4),
        "delta": round(mean(deltas), 4),
        "delta_ci_95": paired_delta_ci_float(deltas),
        "sign_test": task_delta_sign_test(deltas),
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


def paired_delta_ci_float(deltas: List[float]) -> Tuple[float, float]:
    """Approximate 95% CI over task-level deltas."""
    if not deltas:
        return (0.0, 0.0)
    n = len(deltas)
    avg = mean(deltas)
    if n == 1:
        return (round(avg, 4), round(avg, 4))
    variance = sum((d - avg) ** 2 for d in deltas) / (n - 1)
    se = math.sqrt(variance / n)
    return (round(avg - 1.96 * se, 4), round(avg + 1.96 * se, 4))


def task_delta_sign_test(deltas: List[float]) -> Dict:
    """Exact two-sided sign test over non-zero task-level deltas."""
    positive = sum(1 for delta in deltas if delta > 0)
    negative = sum(1 for delta in deltas if delta < 0)
    zero = sum(1 for delta in deltas if delta == 0)
    n = positive + negative
    if n == 0:
        p_value = 1.0
    else:
        k = min(positive, negative)
        p_value = min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / (2**n))
    return {
        "positive_tasks": positive,
        "negative_tasks": negative,
        "zero_delta_tasks": zero,
        "p_value": round(p_value, 4),
        "significant_05": p_value < 0.05,
        "test": "exact two-sided task-cluster sign test",
    }


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
    vtypes: Dict[str, int] = {}

    def add_violation(violation: str, count: int = 1) -> None:
        if not violation:
            key = "UNKNOWN"
        elif ":" in violation:
            key = violation.split(":", 1)[0]
        elif violation.startswith("Unknown action"):
            key = "UNKNOWN_ACTION"
        else:
            key = violation.split(" ", 1)[0]
        vtypes[key] = vtypes.get(key, 0) + count
    
    for r in results:
        for step in r.get("step_details", []):
            for v in step.get("verifier_violations", []):
                add_violation(str(v))
            for repair in step.get("repair_trace", []):
                for v in repair.get("violations", []):
                    add_violation(str(v))
        for vtype, count in r.get("gate_violation_breakdown", {}).items():
            add_violation(str(vtype), int(count))
    
    return dict(sorted(vtypes.items(), key=lambda item: (-item[1], item[0])))


def gate_mechanism_summary(results: List[Dict]) -> Dict:
    valid = [r for r in results if "error" not in r]
    simulations_with_gate_rejections = sum(
        1 for r in valid if int(r.get("gate_rejection_count", 0) or 0) > 0
    )
    return {
        "gate_event_count": sum(int(r.get("gate_event_count", 0) or 0) for r in valid),
        "gate_rejection_count": sum(int(r.get("gate_rejection_count", 0) or 0) for r in valid),
        "gate_repair_attempt_count": sum(int(r.get("gate_repair_attempt_count", 0) or 0) for r in valid),
        "gate_deterministic_repair_count": sum(int(r.get("gate_deterministic_repair_count", 0) or 0) for r in valid),
        "simulations_with_gate_rejections": simulations_with_gate_rejections,
        "tasks_with_gate_rejections": simulations_with_gate_rejections,
    }


def claim_readiness(
    data: Dict[str, List[Dict]],
    left: str = "Schema-Only",
    right: str = "Ours",
    expected_domain: str = "retail",
    expected_task_split_name: str = "base",
) -> Dict:
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
    coverage = pair_coverage(left_results, right_results)
    if not paired_rows:
        return {
            "claim": f"{right} significantly improves task performance over {left}",
            "ready": False,
            "reasons": ["Planner result counts are empty or cannot be paired by task_id."],
        }

    metric = "paper_task_performance"
    effect = paired_effect(left_results, right_results, metric)
    sig = mcnemar_test(left_results, right_results, metric)
    task_effect = task_cluster_effect(left_results, right_results, metric)
    paired_left = [p[0] for p in paired_rows]
    paired_right = [p[1] for p in paired_rows]
    right_success = sum(1 for r in paired_right if metric_value(r, metric))
    left_success = sum(1 for r in paired_left if metric_value(r, metric))
    total = len(paired_rows)
    unique_task_count = len({str(r.get("task_id")) for r in paired_right if r.get("task_id") is not None})
    left_evaluator_names = sorted(set(r.get("evaluator_name", "legacy_or_unknown") for r in paired_left))
    right_evaluator_names = sorted(set(r.get("evaluator_name", "legacy_or_unknown") for r in paired_right))
    evaluator_names = sorted(set(left_evaluator_names + right_evaluator_names))
    official_flags = [
        bool(r.get("official_tau_bench_available", False))
        for r in paired_left + paired_right
    ]
    official_available = all(official_flags)
    uses_official_reward = all(
        str(r.get("evaluator_name", "")).startswith(("official_tau_bench", "official_tau2"))
        for r in paired_left + paired_right
    )
    coverage_warnings = sum(r.get("coverage_warning_count", 0) for r in paired_left + paired_right)
    duplicate_pair_count = max((int(r.get("import_duplicate_pair_count", 0) or 0) for r in paired_left), default=0)
    duplicate_pair_count += max((int(r.get("import_duplicate_pair_count", 0) or 0) for r in paired_right), default=0)
    domains = sorted({str(r.get("domain")) for r in paired_left + paired_right if r.get("domain")})
    task_splits = sorted({str(r.get("task_split_name")) for r in paired_left + paired_right if r.get("task_split_name")})

    reasons = []
    if unique_task_count < 40:
        reasons.append(
            f"Unique paired task coverage is {unique_task_count}; retail tau-bench test evaluation should cover all 40 tasks."
        )
    if total < 40:
        reasons.append(f"Paired simulation count is {total}; expected at least 40 paired simulations.")
    if coverage["left_unpaired_n"] or coverage["right_unpaired_n"]:
        reasons.append(
            "Planner outputs are not fully paired: "
            f"{left} has {coverage['left_unpaired_n']} unpaired rows, "
            f"{right} has {coverage['right_unpaired_n']} unpaired rows."
        )
    if not official_available:
        reasons.append("Official tau-bench package is not available for every paired baseline/proposed result.")
    if not uses_official_reward:
        reasons.append("Baseline and proposed results are not both scored by an official tau-bench reward/evaluator; do not claim official tau-bench task-performance improvement.")
    if "legacy_or_unknown" in evaluator_names:
        reasons.append("Results are legacy/unknown evaluator format; rerun experiments with current code.")
    if effect["delta"] <= 0:
        reasons.append("Task success delta is not positive.")
    if not sig["significant_05"]:
        reasons.append("Task success improvement is not statistically significant at p < 0.05.")
    if task_effect["delta"] <= 0:
        reasons.append("Task-cluster success delta is not positive.")
    if not task_effect["sign_test"]["significant_05"]:
        reasons.append(
            "Task-cluster sign test is not statistically significant at p < 0.05; repeated trials alone are insufficient."
        )
    if coverage_warnings:
        reasons.append(f"Local evaluator emitted {coverage_warnings} coverage warnings.")
    if duplicate_pair_count:
        reasons.append(f"Imported results contained {duplicate_pair_count} duplicate pair_id rows; inspect tau2 outputs before claiming results.")
    if expected_domain and domains and domains != [expected_domain]:
        reasons.append(f"Paired results domain mismatch: expected {expected_domain}, got {domains}.")
    if expected_task_split_name and task_splits and task_splits != [expected_task_split_name]:
        reasons.append(f"Paired results task split mismatch: expected {expected_task_split_name}, got {task_splits}.")

    return {
        "claim": f"{right} significantly improves task performance over {left}",
        "ready": not reasons,
        "left": left,
        "right": right,
        "n": total,
        "pair_coverage": coverage,
        "unique_task_count": unique_task_count,
        "left_success": left_success,
        "right_success": right_success,
        "left_success_ci_95": wilson_ci(left_success, total),
        "right_success_ci_95": wilson_ci(right_success, total),
        "delta": effect["delta"],
        "delta_ci_95": effect["delta_ci_95"],
        "mcnemar": sig,
        "task_cluster_effect": task_effect,
        "metric": metric,
        "evaluator_names": evaluator_names,
        "left_evaluator_names": left_evaluator_names,
        "right_evaluator_names": right_evaluator_names,
        "official_tau_bench_available": official_available,
        "coverage_warnings": coverage_warnings,
        "import_duplicate_pair_count": duplicate_pair_count,
        "domains": domains,
        "task_split_names": task_splits,
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
    if any_result and "local_reward" not in any_result and not is_official_result(any_result):
        print("WARNING: Results do not look like imported official tau2 results.")
        print("         Use import_tau2_results.py before making paper-grade claims.")
    
    # Per-planner summary
    for planner_name, results in data.items():
        valid = [r for r in results if "error" not in r]
        if not valid:
            continue
        
        total = len(valid)
        success = sum(1 for r in valid if r.get("success", False))
        strict_success = sum(1 for r in valid if r.get("strict_success", False))
        has_local_db_metric = any(
            key in r
            for r in valid
            for key in ("local_db_reward", "db_hash_match", "db_state_match")
        )
        local_db_reward = sum(
            1 for r in valid
            if r.get("local_db_reward", r.get("db_hash_match", r.get("db_state_match", False)))
        )
        communication_applicable = [
            r for r in valid
            if r.get("local_communicate_reward") is not None
        ]
        local_communicate_reward = sum(1 for r in communication_applicable if r.get("local_communicate_reward") is True)
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
        total_import_duplicate_pairs = max((int(r.get("import_duplicate_pair_count", 0) or 0) for r in valid), default=0)
        gate_summary = gate_mechanism_summary(valid)
        evaluator_names = sorted(set(r.get("evaluator_name", "legacy_or_unknown") for r in valid))
        official_available = any(r.get("official_tau_bench_available", False) for r in valid)
        official_result = all(is_official_result(r) for r in valid)
        
        print(f"\n{planner_name}:")
        if has_local_db_metric:
            print(f"  Local DB Reward: {local_db_reward}/{total} = {100*local_db_reward/total:.1f}%")
        if communication_applicable:
            print(
                f"  Local Communicate Reward: {local_communicate_reward}/{len(communication_applicable)} "
                f"= {100*local_communicate_reward/len(communication_applicable):.1f}%"
            )
        if official_result:
            print(f"  Official Task Success Rate: {success}/{total} = {100*success/total:.1f}%")
        else:
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
        if gate_summary["gate_event_count"] or gate_summary["gate_rejection_count"]:
            print(f"  Ontology Gate Events: {gate_summary['gate_event_count']}")
            print(f"  Ontology Gate Rejections: {gate_summary['gate_rejection_count']}")
            print(f"  Ontology Gate Repair Attempts: {gate_summary['gate_repair_attempt_count']}")
            print(f"  Ontology Gate Deterministic Repairs: {gate_summary['gate_deterministic_repair_count']}")
            print(
                "  Simulations with Gate Rejections: "
                f"{gate_summary['simulations_with_gate_rejections']}/{total}"
            )
        print(f"  Evaluator: {evaluator_names} (official_tau_bench_available={official_available})")
        print(f"  Coverage Warnings: {total_coverage_warnings}")
        print(f"  Import Duplicate Pair Count: {total_import_duplicate_pairs}")
        
        # Violation breakdown
        vtypes = violation_breakdown(valid)
        if sum(vtypes.values()) > 0:
            print(f"  Violation Breakdown:")
            for vtype, count in vtypes.items():
                if count > 0:
                    print(f"    {vtype}: {count}")
    
    # McNemar tests for available paired planners.
    planner_pairs = [
        ("Schema-Only", "OntologyPrompt"),
        ("OntologyPrompt", "OntologyLite"),
        ("OntologyLite", "Ours"),
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
            metrics = ["paper_task_performance", "success", "strict_success", "final_exact_match", "final_name_match"]
            pair_rows = data[left] + data[right]
            if any(any(k in r for k in ("local_db_reward", "db_hash_match", "db_state_match")) for r in pair_rows):
                metrics.insert(1, "local_db_reward")
            for metric in metrics:
                effect = paired_effect(data[left], data[right], metric)
                mcnemar = mcnemar_test(data[left], data[right], metric)
                task_effect = task_cluster_effect(data[left], data[right], metric)
                print(f"\n  Metric: {metric}")
                print(f"    {left} rate: {effect['schema_rate']*100:.1f}%")
                print(f"    {right} rate: {effect['ours_rate']*100:.1f}%")
                print(f"    Absolute delta: {effect['delta']*100:.1f} pp")
                print(f"    {right} improves: {mcnemar['b_ours_improves']}")
                print(f"    {right} worsens: {mcnemar['c_ours_worsens']}")
                print(f"    Chi-square: {mcnemar['chi2']}")
                print(f"    Exact p-value: {mcnemar['p_value']}")
                print(f"    Significant (p<0.05): {mcnemar['significant_05']}")
                print(f"    Task-cluster delta: {task_effect['delta']*100:.1f} pp")
                print(
                    f"    Task-cluster sign p-value: "
                    f"{task_effect['sign_test']['p_value']}"
                )

    print("\n" + "=" * 70)
    print("CLAIM READINESS")
    print("=" * 70)
    assessment = claim_readiness(data, "Schema-Only", "Ours")
    print(f"Claim: {assessment['claim']}")
    print(f"Ready for main paper claim: {assessment['ready']}")
    if "n" in assessment:
        print(f"  n: {assessment['n']}")
        print(f"  Unique tasks: {assessment.get('unique_task_count', 'unknown')}")
        print(f"  Metric: {assessment.get('metric', 'unknown')}")
        print(
            f"  Success: {assessment['left']}={assessment['left_success']} "
            f"CI95={assessment['left_success_ci_95']} | "
            f"{assessment['right']}={assessment['right_success']} "
            f"CI95={assessment['right_success_ci_95']}"
        )
        print(f"  Delta: {assessment['delta']*100:.1f} pp CI95={assessment['delta_ci_95']}")
        print(f"  McNemar p-value: {assessment['mcnemar']['p_value']}")
        task_effect = assessment["task_cluster_effect"]
        print(
            f"  Task-cluster delta: {task_effect['delta']*100:.1f} pp "
            f"CI95={task_effect['delta_ci_95']}"
        )
        print(
            f"  Task-cluster sign p-value: "
            f"{task_effect['sign_test']['p_value']}"
        )
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
    parser.add_argument(
        "result_dir",
        default="experiments/paper3_agent_planning/results_official_tau2/combined.json",
        nargs="?",
    )
    args = parser.parse_args()
    analyze_experiment(args.result_dir)
