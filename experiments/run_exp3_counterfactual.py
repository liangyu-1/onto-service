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


def main() -> int:
    parser = argparse.ArgumentParser(description="Run experiment 3 (counterfactual)")
    parser.add_argument("--events", default=str(pathlib.Path(__file__).resolve().parent / "configs" / "counterfactual_events.jsonl"))
    parser.add_argument("--run-id", default="")
    args = parser.parse_args()

    run_id = args.run_id or f"exp3_counterfactual_{utc_ts()}"
    out_dir = RESULTS_DIR / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    events = read_jsonl(pathlib.Path(args.events))
    if not events:
        print("No counterfactual events found.")
        return 3

    write_json(
        out_dir / "run_meta.json",
        {
            "run_id": run_id,
            "experiment": "exp3_counterfactual",
            "events_file": args.events,
            "event_count": len(events),
            "environment": snapshot_environment(),
        },
    )

    result = evaluate_all_policies(events, out_dir)
    summaries = result["summary"]
    write_json(out_dir / "summary.json", {"run_id": run_id, "summaries": summaries})

    # Scenario-level export to support write-up around "edit-count decoupling".
    rows: List[Dict[str, Any]] = []
    for policy_summary in summaries:
        policy = policy_summary["policy"]
        for step in read_jsonl(out_dir / f"steps_{policy}.jsonl"):
            scenario = next((e.get("scenario", "unknown") for e in events if e.get("workload_id") == step.get("workload_id")), "unknown")
            rows.append(
                {
                    "policy": policy,
                    "scenario": scenario,
                    "workload_id": step.get("workload_id"),
                    "chosen_action": step.get("chosen_action"),
                    "oracle_action": step.get("oracle_action"),
                    "chosen_utility": step.get("chosen_utility"),
                    "regret": max(0.0, float(step.get("oracle_utility", 0.0)) - float(step.get("chosen_utility", 0.0))),
                }
            )
    write_csv(out_dir / "counterfactual_scenario_matrix.csv", rows, ["policy", "scenario", "workload_id", "chosen_action", "oracle_action", "chosen_utility", "regret"])
    print(f"exp3 done: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

