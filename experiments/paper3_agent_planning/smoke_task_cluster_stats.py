#!/usr/bin/env python3
"""Smoke tests for task-cluster significance analysis."""
from __future__ import annotations

from analyze_results import claim_readiness, task_cluster_effect


def official_row(task_id: str, trial_id: int, planner: str, success: bool, gate: bool = False) -> dict:
    return {
        "task_id": task_id,
        "trial_id": str(trial_id),
        "pair_id": f"{task_id}::trial={trial_id}",
        "planner": planner,
        "domain": "retail",
        "task_split_name": "base",
        "official_reward": 1.0 if success else 0.0,
        "official_success": success,
        "success": success,
        "strict_success": success,
        "evaluator_name": "official_tau2_reward",
        "official_tau_bench_available": True,
        "coverage_warning_count": 0,
        "gate_event_count": 1 if gate else 0,
    }


def build_all_improve_case() -> dict:
    left = []
    right = []
    for task_idx in range(40):
        task_id = f"task_{task_idx:03d}"
        left.append(official_row(task_id, 0, "Schema-Only", False))
        right.append(official_row(task_id, 0, "Ours", True, gate=True))
    return {"Schema-Only": left, "Ours": right}


def build_pseudoreplication_case() -> dict:
    left = []
    right = []
    for task_idx in range(2):
        task_id = f"task_{task_idx:03d}"
        for trial_id in range(40):
            left.append(official_row(task_id, trial_id, "Schema-Only", False))
            right.append(official_row(task_id, trial_id, "Ours", True, gate=True))
    return {"Schema-Only": left, "Ours": right}


def main() -> None:
    all_improve = build_all_improve_case()
    ready = claim_readiness(all_improve)
    if not ready["ready"]:
        raise AssertionError(f"expected all-improve case to pass, got {ready['reasons']}")
    effect = task_cluster_effect(
        all_improve["Schema-Only"],
        all_improve["Ours"],
        "paper_task_performance",
    )
    if effect["n_tasks"] != 40 or not effect["sign_test"]["significant_05"]:
        raise AssertionError(f"expected significant 40-task effect, got {effect}")

    pseudo = build_pseudoreplication_case()
    rejected = claim_readiness(pseudo)
    if rejected["ready"]:
        raise AssertionError("expected pseudo-replicated two-task case to be rejected")
    if not any("Unique paired task coverage is 2" in reason for reason in rejected["reasons"]):
        raise AssertionError(f"expected unique-task rejection, got {rejected['reasons']}")
    if not any("Task-cluster sign test" in reason for reason in rejected["reasons"]):
        raise AssertionError(f"expected task-cluster significance rejection, got {rejected['reasons']}")

    mixed_evaluator = build_all_improve_case()
    for row in mixed_evaluator["Schema-Only"]:
        row["evaluator_name"] = "legacy_or_unknown"
        row["official_tau_bench_available"] = False
    rejected_mixed = claim_readiness(mixed_evaluator)
    if rejected_mixed["ready"]:
        raise AssertionError("expected mixed official/non-official evaluator case to be rejected")
    if not any("Baseline and proposed results are not both scored" in reason for reason in rejected_mixed["reasons"]):
        raise AssertionError(f"expected mixed evaluator rejection, got {rejected_mixed['reasons']}")

    duplicate_import = build_all_improve_case()
    for row in duplicate_import["Ours"]:
        row["import_duplicate_pair_count"] = 1
    rejected_duplicate = claim_readiness(duplicate_import)
    if rejected_duplicate["ready"]:
        raise AssertionError("expected duplicate imported pair case to be rejected")
    if not any("duplicate pair_id" in reason for reason in rejected_duplicate["reasons"]):
        raise AssertionError(f"expected duplicate pair rejection, got {rejected_duplicate['reasons']}")

    unpaired = build_all_improve_case()
    unpaired["Schema-Only"] = unpaired["Schema-Only"][:-1]
    rejected_unpaired = claim_readiness(unpaired)
    if rejected_unpaired["ready"]:
        raise AssertionError("expected unpaired left/right results to be rejected")
    if not any("not fully paired" in reason for reason in rejected_unpaired["reasons"]):
        raise AssertionError(f"expected unpaired rejection, got {rejected_unpaired['reasons']}")

    wrong_split = build_all_improve_case()
    for row in wrong_split["Ours"]:
        row["task_split_name"] = "dev"
    rejected_split = claim_readiness(wrong_split)
    if rejected_split["ready"]:
        raise AssertionError("expected wrong split case to be rejected")
    if not any("task split mismatch" in reason for reason in rejected_split["reasons"]):
        raise AssertionError(f"expected split mismatch rejection, got {rejected_split['reasons']}")

    print("task-cluster statistics smoke tests passed")


if __name__ == "__main__":
    main()
