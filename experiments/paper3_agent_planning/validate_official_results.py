#!/usr/bin/env python3
"""Fail-fast validator for official tau2/tau3 paired experiment results."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Dict, List

BASE_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from analyze_results import claim_readiness, paired_by_task_id  # noqa: E402


def load_combined(path: pathlib.Path) -> Dict[str, List[Dict]]:
    with open(path) as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Combined result file must be a planner-name -> result-list JSON object.")
    return data


def validate(
    data: Dict[str, List[Dict]],
    left: str,
    right: str,
    min_unique_tasks: int,
    min_paired_simulations: int,
    alpha: float,
    require_gate_trace: bool = False,
) -> Dict:
    if left not in data:
        raise ValueError(f"Missing left planner: {left}")
    if right not in data:
        raise ValueError(f"Missing right planner: {right}")

    pairs = paired_by_task_id(data[left], data[right])
    unique_tasks = {str(r.get("task_id")) for _, r in pairs if r.get("task_id") is not None}
    assessment = claim_readiness(data, left, right)

    failures = list(assessment.get("reasons", []))
    if len(unique_tasks) < min_unique_tasks:
        failures.append(f"Only {len(unique_tasks)} unique paired tasks; required {min_unique_tasks}.")
    if len(pairs) < min_paired_simulations:
        failures.append(f"Only {len(pairs)} paired simulations; required {min_paired_simulations}.")
    p_value = assessment.get("mcnemar", {}).get("p_value", 1.0)
    task_p_value = (
        assessment.get("task_cluster_effect", {})
        .get("sign_test", {})
        .get("p_value", 1.0)
    )
    if p_value >= alpha:
        failures.append(f"McNemar p-value {p_value} is not below alpha={alpha}.")
    if task_p_value >= alpha:
        failures.append(f"Task-cluster sign-test p-value {task_p_value} is not below alpha={alpha}.")
    if require_gate_trace:
        right_paired = [right_row for _, right_row in pairs]
        gate_events = sum(int(r.get("gate_event_count", 0) or 0) for r in right_paired)
        if gate_events <= 0:
            failures.append(
                f"No ontology gate trace was found for {right}; task success may be official, but mechanism analysis is unsupported."
            )

    deduped_failures = []
    seen = set()
    for failure in failures:
        if failure in seen:
            continue
        seen.add(failure)
        deduped_failures.append(failure)

    return {
        "ready": not deduped_failures,
        "left": left,
        "right": right,
        "paired_simulations": len(pairs),
        "unique_tasks": len(unique_tasks),
        "alpha": alpha,
        "require_gate_trace": require_gate_trace,
        "assessment": assessment,
        "failures": deduped_failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate official tau2/tau3 paired results before paper use.")
    parser.add_argument("combined_json", help="Combined JSON produced by import_tau2_results.py")
    parser.add_argument("--left", default="Schema-Only")
    parser.add_argument("--right", default="Ours")
    parser.add_argument("--min-unique-tasks", type=int, default=40)
    parser.add_argument("--min-paired-simulations", type=int, default=40)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument(
        "--require-gate-trace",
        action="store_true",
        help="Also require ontology gate traces for the proposed planner.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable validation output.")
    args = parser.parse_args()

    report = validate(
        load_combined(pathlib.Path(args.combined_json)),
        left=args.left,
        right=args.right,
        min_unique_tasks=args.min_unique_tasks,
        min_paired_simulations=args.min_paired_simulations,
        alpha=args.alpha,
        require_gate_trace=args.require_gate_trace,
    )
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"Ready: {report['ready']}")
        print(f"Paired simulations: {report['paired_simulations']}")
        print(f"Unique tasks: {report['unique_tasks']}")
        print(f"Alpha: {report['alpha']}")
        print(f"Require gate trace: {report['require_gate_trace']}")
        if report["failures"]:
            print("Failures:")
            for failure in report["failures"]:
                print(f"  - {failure}")

    if not report["ready"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
