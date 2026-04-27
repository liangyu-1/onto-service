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
    parser = argparse.ArgumentParser(description="Run experiment 4 (leave-one-ontology-out)")
    parser.add_argument("--events", default=str(pathlib.Path(__file__).resolve().parent / "configs" / "replay_events.jsonl"))
    parser.add_argument("--run-id", default="")
    args = parser.parse_args()

    run_id = args.run_id or f"exp4_generalization_{utc_ts()}"
    out_dir = RESULTS_DIR / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    all_events = read_jsonl(pathlib.Path(args.events))
    if not all_events:
        print("No events found.")
        return 3

    domains = sorted({str(e.get("domain")) for e in all_events if e.get("domain")})
    if len(domains) < 2:
        print("Need at least two domains for leave-one-ontology-out.")
        return 4

    write_json(
        out_dir / "run_meta.json",
        {
            "run_id": run_id,
            "experiment": "exp4_generalization",
            "events_file": args.events,
            "domains": domains,
            "environment": snapshot_environment(),
        },
    )

    summary_rows: List[Dict[str, Any]] = []
    for held_out in domains:
        fold_dir = out_dir / f"held_out_{held_out}"
        fold_dir.mkdir(parents=True, exist_ok=True)
        train = [e for e in all_events if e.get("domain") != held_out]
        test = [e for e in all_events if e.get("domain") == held_out]

        # This framework keeps policy parameters fixed; train set is logged for traceability.
        write_json(fold_dir / "split_meta.json", {"held_out": held_out, "train_size": len(train), "test_size": len(test)})
        result = evaluate_all_policies(test, fold_dir)
        for item in result["summary"]:
            row = dict(item)
            row["held_out_domain"] = held_out
            summary_rows.append(row)

    write_csv(
        out_dir / "generalization_summary.csv",
        summary_rows,
        [
            "held_out_domain",
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
        ],
    )
    print(f"exp4 done: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

