from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Any, Dict, List

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.common import RESULTS_DIR, read_jsonl, snapshot_environment, utc_ts, write_csv, write_json, write_jsonl
from experiments.preflight import run_preflight
from experiments.runner import evaluate_all_policies


def build_curve_sources(out_dir: pathlib.Path, summaries: List[Dict[str, Any]]) -> None:
    curve_rows: List[Dict[str, Any]] = []
    regret_rows: List[Dict[str, Any]] = []
    utr_rows: List[Dict[str, Any]] = []
    hit_rows: List[Dict[str, Any]] = []

    for summary in summaries:
        policy = summary["policy"]
        step_file = out_dir / f"steps_{policy}.jsonl"
        steps = read_jsonl(step_file)
        cnu = 0.0
        for step in steps:
            cnu += float(step.get("chosen_utility", 0.0))
            regret = max(0.0, float(step.get("oracle_utility", 0.0)) - float(step.get("chosen_utility", 0.0)))
            curve_rows.append({"policy": policy, "step": step["step"], "cumulative_utility": cnu})
            regret_rows.append({"policy": policy, "step": step["step"], "regret": regret})
            utr_rows.append(
                {
                    "policy": policy,
                    "step": step["step"],
                    "utr_flag": 1
                    if step.get("chosen_action") != "no_op"
                    and (step.get("oracle_action") == "no_op" or float(step.get("chosen_utility", 0.0)) < float(step.get("no_op_utility", 0.0)))
                    else 0,
                }
            )
            hit_rows.append({"policy": policy, "step": step["step"], "hit_flag": 1 if step.get("chosen_action") == step.get("oracle_action") else 0})

    write_csv(out_dir / "curve_cumulative_utility.csv", curve_rows, ["policy", "step", "cumulative_utility"])
    write_csv(out_dir / "box_regret_source.csv", regret_rows, ["policy", "step", "regret"])
    write_csv(out_dir / "bar_utr_source.csv", utr_rows, ["policy", "step", "utr_flag"])
    write_csv(out_dir / "line_hit_rate_source.csv", hit_rows, ["policy", "step", "hit_flag"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Run experiment 1 and 2 (replay + decision quality)")
    parser.add_argument("--api-base", default="http://localhost:8080/api/v1")
    parser.add_argument("--events", default=str(pathlib.Path(__file__).resolve().parent / "configs" / "replay_events.jsonl"))
    parser.add_argument("--run-id", default="")
    args = parser.parse_args()

    run_id = args.run_id or f"exp1_exp2_{utc_ts()}"
    out_dir = RESULTS_DIR / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    preflight = run_preflight(args.api_base)
    write_json(out_dir / "preflight_report.json", preflight)
    if not preflight["ok"]:
        print("Preflight failed. stop.")
        return 2

    events = read_jsonl(pathlib.Path(args.events))
    if not events:
        print("No events found.")
        return 3

    run_meta = {
        "run_id": run_id,
        "experiment": "exp1_exp2",
        "events_file": args.events,
        "event_count": len(events),
        "environment": snapshot_environment(),
    }
    write_json(out_dir / "run_meta.json", run_meta)

    result = evaluate_all_policies(events, out_dir)
    summaries = result["summary"]
    write_json(out_dir / "summary.json", {"run_id": run_id, "summaries": summaries})
    build_curve_sources(out_dir, summaries)
    print(f"exp1_exp2 done: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

