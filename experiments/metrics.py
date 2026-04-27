from __future__ import annotations

import math
import statistics
from typing import Any, Dict, Iterable, List


def _safe_mean(values: Iterable[float]) -> float:
    vals = list(values)
    return statistics.fmean(vals) if vals else 0.0


def _percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    rank = (len(ordered) - 1) * p
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return ordered[low]
    w = rank - low
    return ordered[low] * (1.0 - w) + ordered[high] * w


def summarize_policy_steps(steps: List[Dict[str, Any]]) -> Dict[str, Any]:
    regrets = [max(0.0, float(s.get("oracle_utility", 0.0)) - float(s.get("chosen_utility", 0.0))) for s in steps]
    chosen_utils = [float(s.get("chosen_utility", 0.0)) for s in steps]
    latencies = [float(s.get("latency_ms", 0.0)) for s in steps]
    rebuilds = [float(s.get("rebuild_ms", 0.0)) for s in steps]
    storage = [float(s.get("storage_overhead_mb", 0.0)) for s in steps]
    consistency = [1.0 if bool(s.get("consistency_violation", False)) else 0.0 for s in steps]
    bias = [abs(float(s.get("estimated_utility", 0.0)) - float(s.get("chosen_utility", 0.0))) for s in steps]
    hits = [1.0 if s.get("chosen_action") == s.get("oracle_action") else 0.0 for s in steps]
    unnecessary = [
        1.0
        if s.get("chosen_action") != "no_op" and (s.get("oracle_action") == "no_op" or float(s.get("chosen_utility", 0.0)) < float(s.get("no_op_utility", 0.0)))
        else 0.0
        for s in steps
    ]

    return {
        "steps": len(steps),
        "avg_regret": _safe_mean(regrets),
        "cnu": float(sum(chosen_utils)),
        "utr": _safe_mean(unnecessary),
        "hit_rate": _safe_mean(hits),
        "latency_p50_ms": _percentile(latencies, 0.5),
        "latency_p95_ms": _percentile(latencies, 0.95),
        "avg_rebuild_ms": _safe_mean(rebuilds),
        "avg_storage_overhead_mb": _safe_mean(storage),
        "bias_rate": _safe_mean(bias),
        "consistency_violation_rate": _safe_mean(consistency),
    }

