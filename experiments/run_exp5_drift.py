from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Any, Dict, List

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.common import RESULTS_DIR, read_jsonl, snapshot_environment, utc_ts, write_csv, write_json
from experiments.runner import evaluate_all_policies


def build_drift_series(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not events:
        return []
    phases = [
        ("stable", 0.00, 1.00),
        ("shift_a", 0.18, 1.12),
        ("shift_b", 0.34, 1.25),
    ]
    out: List[Dict[str, Any]] = []
    for idx, e in enumerate(events):
        phase_name, pressure_delta, latency_mul = phases[idx % len(phases)]
        copied = dict(e)
        copied["phase"] = phase_name
        copied["workload_pressure"] = max(0.0, min(1.0, float(copied.get("workload_pressure", 0.3)) + pressure_delta))
        copied["base_latency_ms"] = float(copied.get("base_latency_ms", 100.0)) * latency_mul
        out.append(copied)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Run experiment 5 (workload drift)")
    parser.add_argument("--events", default=str(pathlib.Path(__file__).resolve().parent / "configs" / "replay_events.jsonl"))
    parser.add_argument("--run-id", default="")
    args = parser.parse_args()

    run_id = args.run_id or f"exp5_drift_{utc_ts()}"
    out_dir = RESULTS_DIR / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    base_events = read_jsonl(pathlib.Path(args.events))
    if not base_events:
        print("No events found.")
        return 3

    drift_events = build_drift_series(base_events)
    write_json(
        out_dir / "run_meta.json",
        {
            "run_id": run_id,
            "experiment": "exp5_drift",
            "events_file": args.events,
            "event_count": len(drift_events),
            "environment": snapshot_environment(),
        },
    )
    write_json(out_dir / "drift_events_preview.json", drift_events[:5])

    result = evaluate_all_policies(drift_events, out_dir)
    summaries = result["summary"]
    write_json(out_dir / "summary.json", {"run_id": run_id, "summaries": summaries})

    phase_rows: List[Dict[str, Any]] = []
    for summary in summaries:
        policy = summary["policy"]
        steps = read_jsonl(out_dir / f"steps_{policy}.jsonl")
        for step in steps:
            phase = next((evt.get("phase", "unknown") for evt in drift_events if evt.get("workload_id") == step.get("workload_id")), "unknown")
            phase_rows.append(
                {
                    "policy": policy,
                    "phase": phase,
                    "step": step["step"],
                    "latency_ms": step["latency_ms"],
                    "regret": max(0.0, float(step.get("oracle_utility", 0.0)) - float(step.get("chosen_utility", 0.0))),
                    "hit": 1 if step.get("chosen_action") == step.get("oracle_action") else 0,
                }
            )

    write_csv(out_dir / "drift_phase_metrics.csv", phase_rows, ["policy", "phase", "step", "latency_ms", "regret", "hit"])
    print(f"exp5 done: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

