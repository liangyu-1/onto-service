#!/usr/bin/env python3
"""Convert official tau2/tau3 trajectory results into this experiment format.

The local runner stores results as:

    {"Schema-Only": [...], "Ours": [...]}

Official tau2 runs may store simulations as a monolithic JSON file or as a
directory of per-task JSON files. This importer extracts only paper-grade
fields that are needed for paired significance analysis. It deliberately marks
the evaluator as official only when a numeric official reward is present.
"""
from __future__ import annotations

import argparse
import json
import pathlib
from collections import Counter
from typing import Any, Dict, Iterable, List


def iter_json_files(path: pathlib.Path) -> Iterable[pathlib.Path]:
    if path.is_file():
        yield path
        return
    for file_path in sorted(path.rglob("*.json")):
        yield file_path


def load_json_documents(path: pathlib.Path) -> Iterable[Any]:
    for file_path in iter_json_files(path):
        with open(file_path) as f:
            try:
                yield json.load(f)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Failed to parse JSON file {file_path}: {exc}") from exc


def candidate_simulations(document: Any) -> Iterable[Dict[str, Any]]:
    """Yield simulation-like dicts from common tau2 result wrappers."""
    if isinstance(document, list):
        for item in document:
            if isinstance(item, dict):
                yield from candidate_simulations(item)
        return
    if not isinstance(document, dict):
        return

    if looks_like_simulation(document):
        yield document

    for key in ("simulations", "results", "runs", "data"):
        value = document.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    yield from candidate_simulations(item)
        elif isinstance(value, dict):
            yield from candidate_simulations(value)


def looks_like_simulation(item: Dict[str, Any]) -> bool:
    if "reward_info" in item or "reward" in item:
        return bool(extract_task_id(item))
    return False


def extract_task_id(sim: Dict[str, Any]) -> str:
    for key in ("task_id", "id"):
        value = sim.get(key)
        if value is not None:
            return str(value)
    task = sim.get("task")
    if isinstance(task, dict):
        for key in ("id", "task_id"):
            value = task.get(key)
            if value is not None:
                return str(value)
    return ""


def extract_trial_id(sim: Dict[str, Any], fallback: int) -> str:
    for key in ("trial_id", "trial", "trial_idx", "run_id", "seed"):
        value = sim.get(key)
        if value is not None:
            return str(value)
    info = sim.get("info")
    if isinstance(info, dict):
        for key in ("trial_id", "trial", "trial_idx", "run_id", "seed"):
            value = info.get(key)
            if value is not None:
                return str(value)
    return str(fallback)


def extract_metadata(sim: Dict[str, Any], key: str) -> str:
    for source in (
        sim,
        sim.get("task") if isinstance(sim.get("task"), dict) else {},
        sim.get("info") if isinstance(sim.get("info"), dict) else {},
        sim.get("config") if isinstance(sim.get("config"), dict) else {},
        sim.get("run_config") if isinstance(sim.get("run_config"), dict) else {},
    ):
        if isinstance(source, dict):
            value = source.get(key)
            if value is not None:
                return str(value)
    return ""


def extract_reward_info(sim: Dict[str, Any]) -> Dict[str, Any]:
    reward_info = sim.get("reward_info")
    if isinstance(reward_info, dict):
        return reward_info
    reward = sim.get("reward")
    if isinstance(reward, (int, float, bool)):
        return {"reward": float(reward)}
    return {}


def iter_dicts(value: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from iter_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_dicts(child)


def extract_ontology_gate_trace(sim: Dict[str, Any]) -> Dict[str, Any]:
    """Extract mechanism traces emitted by tau2_ontology_agent when present.

    Tau2/tau3 result schemas vary across versions. Instead of assuming a fixed
    message path, recursively scan the simulation JSON for raw_data-like dicts
    containing the `ontology_gate` object emitted by the custom agent.
    """
    gate_events: List[Dict[str, Any]] = []
    for item in iter_dicts(sim):
        gate = item.get("ontology_gate")
        if isinstance(gate, dict) and gate.get("enabled") is True:
            gate_events.append(gate)

    violation_counter: Counter[str] = Counter()
    rejected_candidates: List[Dict[str, Any]] = []
    deterministic_repair_count = 0
    for event in gate_events:
        for rejected in event.get("rejected_candidates", []) or []:
            if not isinstance(rejected, dict):
                continue
            rejected_candidates.append(rejected)
            repair_candidate = (
                rejected.get("ontology_repair_candidate")
                or rejected.get("deterministic_repair_candidate")
            )
            repair_violations = (
                rejected.get("ontology_repair_violations")
                if "ontology_repair_violations" in rejected
                else rejected.get("deterministic_repair_violations")
            )
            if repair_candidate and not repair_violations:
                deterministic_repair_count += 1
            for violation in rejected.get("violations", []) or []:
                violation_counter[violation_type(str(violation))] += 1

    return {
        "gate_event_count": len(gate_events),
        "gate_rejection_count": len(rejected_candidates),
        "gate_repair_attempt_count": sum(int(event.get("repair_attempt_count", 0) or 0) for event in gate_events),
        "gate_deterministic_repair_count": deterministic_repair_count,
        "gate_selected_actions": [
            event.get("selected_action")
            for event in gate_events
            if event.get("selected_action")
        ],
        "gate_violation_breakdown": dict(sorted(violation_counter.items())),
        "gate_rejected_candidates": rejected_candidates,
    }


def violation_type(violation: str) -> str:
    if ":" in violation:
        return violation.split(":", 1)[0]
    if violation.startswith("Unknown action"):
        return "UNKNOWN_ACTION"
    return violation.split(" ", 1)[0] if violation else "UNKNOWN"


def normalize_tau2_result(
    sim: Dict[str, Any],
    planner_name: str,
    fallback_trial_id: int,
    domain: str = "",
    task_split_name: str = "",
) -> Dict[str, Any]:
    task_id = extract_task_id(sim)
    trial_id = extract_trial_id(sim, fallback_trial_id)
    reward_info = extract_reward_info(sim)
    reward = reward_info.get("reward")
    if not isinstance(reward, (int, float, bool)):
        raise ValueError(f"Simulation for task {task_id or '<unknown>'} has no numeric reward_info.reward")
    reward_float = float(reward)
    reward_breakdown = reward_info.get("reward_breakdown") or {}
    reward_basis = reward_info.get("reward_basis")
    if reward_basis is None:
        task = sim.get("task") if isinstance(sim.get("task"), dict) else {}
        criteria = task.get("evaluation_criteria") if isinstance(task, dict) else {}
        reward_basis = criteria.get("reward_basis") if isinstance(criteria, dict) else None

    row = {
        "task_id": task_id,
        "trial_id": trial_id,
        "pair_id": f"{task_id}::trial={trial_id}",
        "planner": planner_name,
        "domain": extract_metadata(sim, "domain") or domain,
        "task_split_name": (
            extract_metadata(sim, "task_split_name")
            or extract_metadata(sim, "task_split")
            or extract_metadata(sim, "split")
            or task_split_name
        ),
        "official_reward": reward_float,
        "official_success": reward_float >= 1.0,
        "success": reward_float >= 1.0,
        "strict_success": reward_float >= 1.0,
        "reward_basis": reward_basis or [],
        "official_reward_breakdown": reward_breakdown,
        "evaluator_name": "official_tau2_reward",
        "evaluator_scope": "Official tau2/tau3 reward_info.reward imported from trajectory output.",
        "official_tau_bench_available": True,
        "coverage_warning_count": 0,
        "raw_termination_reason": sim.get("termination_reason"),
    }
    row.update(extract_ontology_gate_trace(sim))
    return row


def import_planner_results(
    path: pathlib.Path,
    planner_name: str,
    domain: str = "",
    task_split_name: str = "",
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    seen_pair_ids = set()
    duplicate_pair_count = 0
    fallback_counts: Dict[str, int] = {}
    for document in load_json_documents(path):
        for sim in candidate_simulations(document):
            task_id = extract_task_id(sim)
            fallback_trial_id = fallback_counts.get(task_id, 0)
            fallback_counts[task_id] = fallback_trial_id + 1
            row = normalize_tau2_result(
                sim,
                planner_name,
                fallback_trial_id,
                domain=domain,
                task_split_name=task_split_name,
            )
            task_id = row["task_id"]
            if not task_id:
                continue
            if row["pair_id"] in seen_pair_ids:
                duplicate_pair_count += 1
                continue
            seen_pair_ids.add(row["pair_id"])
            rows.append(row)
    for row in rows:
        row["import_duplicate_pair_count"] = duplicate_pair_count
    return sorted(rows, key=lambda r: (str(r["task_id"]), str(r.get("trial_id", ""))))


def main() -> None:
    parser = argparse.ArgumentParser(description="Import official tau2/tau3 results for paired analysis.")
    parser.add_argument("--left-path", required=True, help="Official tau2 result file/dir for baseline planner.")
    parser.add_argument("--left-name", default="Schema-Only", help="Planner name for left/baseline results.")
    parser.add_argument("--right-path", required=True, help="Official tau2 result file/dir for proposed planner.")
    parser.add_argument("--right-name", default="Ours", help="Planner name for right/proposed results.")
    parser.add_argument("--domain", default="", help="Expected tau2 domain to attach when missing from result files.")
    parser.add_argument("--task-split-name", default="", help="Expected tau2 task split to attach when missing from result files.")
    parser.add_argument(
        "--extra",
        action="append",
        default=[],
        metavar="NAME=PATH",
        help="Additional planner result file/dir to import, repeatable.",
    )
    parser.add_argument("--output", required=True, help="Output combined JSON path.")
    args = parser.parse_args()

    imported = {
        args.left_name: import_planner_results(pathlib.Path(args.left_path), args.left_name, args.domain, args.task_split_name),
        args.right_name: import_planner_results(pathlib.Path(args.right_path), args.right_name, args.domain, args.task_split_name),
    }
    for spec in args.extra:
        if "=" not in spec:
            raise ValueError(f"--extra must use NAME=PATH format, got {spec!r}")
        name, path = spec.split("=", 1)
        if not name or not path:
            raise ValueError(f"--extra must use NAME=PATH format, got {spec!r}")
        imported[name] = import_planner_results(pathlib.Path(path), name, args.domain, args.task_split_name)

    for planner_name, rows in imported.items():
        if not rows:
            raise RuntimeError(f"No official simulations imported for {planner_name}")

    output = pathlib.Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w") as f:
        json.dump(imported, f, indent=2, ensure_ascii=False)

    for planner_name, rows in imported.items():
        print(f"Imported {len(rows)} {planner_name} rows")
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
