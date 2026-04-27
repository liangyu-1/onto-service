from __future__ import annotations

import pathlib
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List

from experiments.common import utc_ts, write_csv, write_json, write_jsonl
from experiments.metrics import summarize_policy_steps
from experiments.policies import ACTIONS, OraclePolicy, PolicyContext, build_policies


@dataclass
class RewardWeights:
    query_gain: float = 1.0
    rebuild_cost: float = 0.002
    storage_cost: float = 0.02
    consistency_cost: float = 1.0


def estimate_action_scores(event: Dict[str, Any], candidates: List[str], weights: RewardWeights) -> Dict[str, float]:
    base_latency = float(event.get("base_latency_ms", 100.0))
    significance = float(event.get("semantic_significance", 0.1))
    workload_pressure = float(event.get("workload_pressure", 0.3))
    edit_count = float(event.get("edit_count", 0.0))

    action_meta = {
        "no_op": {"gain_factor": 0.0, "rebuild": 0.0, "storage": 0.0, "risk": 0.0},
        "refresh_mv": {"gain_factor": 0.35, "rebuild": 220.0, "storage": 5.0, "risk": 0.02},
        "repartition": {"gain_factor": 0.45, "rebuild": 280.0, "storage": 7.0, "risk": 0.03},
        "reindex": {"gain_factor": 0.30, "rebuild": 160.0, "storage": 3.0, "risk": 0.02},
        "cache_plan": {"gain_factor": 0.20, "rebuild": 60.0, "storage": 1.0, "risk": 0.01},
    }

    scores: Dict[str, float] = {}
    for action in candidates:
        meta = action_meta[action]
        query_gain = base_latency * meta["gain_factor"] * (0.5 + significance + workload_pressure + (edit_count / 20.0))
        utility = (
            weights.query_gain * query_gain
            - weights.rebuild_cost * meta["rebuild"]
            - weights.storage_cost * meta["storage"]
            - weights.consistency_cost * meta["risk"]
        )
        scores[action] = utility
    return scores


def true_utility(event: Dict[str, Any], action: str, estimated: float) -> float:
    # Ground-truth utility can diverge from estimator via per-event action_effects.
    effects = event.get("action_effects", {})
    if action in effects:
        return float(effects[action])
    return estimated


def action_runtime_meta(action: str) -> Dict[str, Any]:
    table = {
        "no_op": {"rebuild_ms": 0.0, "storage_overhead_mb": 0.0, "consistency_violation": False},
        "refresh_mv": {"rebuild_ms": 220.0, "storage_overhead_mb": 5.0, "consistency_violation": False},
        "repartition": {"rebuild_ms": 280.0, "storage_overhead_mb": 7.0, "consistency_violation": False},
        "reindex": {"rebuild_ms": 160.0, "storage_overhead_mb": 3.0, "consistency_violation": False},
        "cache_plan": {"rebuild_ms": 60.0, "storage_overhead_mb": 1.0, "consistency_violation": False},
    }
    return table.get(action, table["no_op"])


def evaluate_policy(name: str, events: Iterable[Dict[str, Any]], out_dir: pathlib.Path) -> Dict[str, Any]:
    weights = RewardWeights()
    candidates = ACTIONS[:]
    policies = {p.name: p for p in build_policies()}
    oracle = OraclePolicy()
    if name not in policies:
        raise ValueError(f"Unknown policy: {name}")
    policy = policies[name]

    steps: List[Dict[str, Any]] = []
    for idx, event in enumerate(events):
        scores = estimate_action_scores(event, candidates, weights)
        ctx = PolicyContext(step_idx=idx, event=event, candidates=candidates, scores=scores)

        chosen_action = policy.choose_action(ctx)
        oracle_action = oracle.choose_action(ctx)
        est_utility = float(scores.get(chosen_action, -1e9))
        chosen_utility = true_utility(event, chosen_action, est_utility)
        oracle_utility = true_utility(event, oracle_action, float(scores.get(oracle_action, -1e9)))
        no_op_utility = true_utility(event, "no_op", float(scores.get("no_op", 0.0)))

        base_latency = float(event.get("base_latency_ms", 100.0))
        speedup = float(event.get("latency_speedup", {}).get(chosen_action, 0.0))
        latency_ms = max(5.0, base_latency - speedup)

        runtime = action_runtime_meta(chosen_action)
        steps.append(
            {
                "step": idx,
                "policy": name,
                "domain": event.get("domain"),
                "version": event.get("version"),
                "workload_id": event.get("workload_id"),
                "chosen_action": chosen_action,
                "oracle_action": oracle_action,
                "estimated_utility": est_utility,
                "chosen_utility": chosen_utility,
                "oracle_utility": oracle_utility,
                "no_op_utility": no_op_utility,
                "latency_ms": latency_ms,
                "rebuild_ms": runtime["rebuild_ms"],
                "storage_overhead_mb": runtime["storage_overhead_mb"],
                "consistency_violation": runtime["consistency_violation"],
                "executedSql": event.get("executed_sql", ""),
            }
        )

    summary = summarize_policy_steps(steps)
    summary["policy"] = name
    write_jsonl(out_dir / f"steps_{name}.jsonl", steps)
    write_json(out_dir / f"summary_{name}.json", summary)
    return summary


def evaluate_all_policies(events: List[Dict[str, Any]], out_dir: pathlib.Path) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    summaries: List[Dict[str, Any]] = []
    for policy_name in [p.name for p in build_policies()]:
        summaries.append(evaluate_policy(policy_name, events, out_dir))

    columns = [
        "policy",
        "steps",
        "avg_regret",
        "cnu",
        "utr",
        "hit_rate",
        "latency_p50_ms",
        "latency_p95_ms",
        "avg_rebuild_ms",
        "avg_storage_overhead_mb",
        "bias_rate",
        "consistency_violation_rate",
    ]
    write_csv(out_dir / "summary.csv", summaries, columns)
    return {"run_id": utc_ts(), "summary": summaries}

