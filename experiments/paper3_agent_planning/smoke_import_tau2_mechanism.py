#!/usr/bin/env python3
"""Smoke test official-result import of ontology gate mechanism traces."""
from __future__ import annotations

import json
import pathlib
import tempfile

from import_tau2_results import import_planner_results


def main() -> None:
    sim = {
        "task_id": "retail_001",
        "trial_id": 0,
        "reward_info": {"reward": 1.0},
        "messages": [
            {
                "role": "assistant",
                "raw_data": {
                    "agent_kind": "ontology",
                    "ontology_gate": {
                        "enabled": True,
                        "selected_action": "find_user_id_by_name_zip",
                        "selected_arguments": {
                            "first_name": "Jane",
                            "last_name": "Doe",
                            "zip": "02139",
                        },
                        "rejection_count": 1,
                        "repair_attempt_count": 1,
                        "rejected_candidates": [
                            {
                                "attempt": 0,
                                "candidate": {
                                    "action": "find_user_id_by_name_zip",
                                    "arguments": {"first_name": "Jane", "last_name": "Doe"},
                                },
                                "violations": ["MISSING_PARAMETER: find_user_id_by_name_zip.zip"],
                                "deterministic_repair_candidate": {
                                    "action": "ask_for_confirmation",
                                    "arguments": {"action_description": "confirm"},
                                },
                                "deterministic_repair_violations": [],
                            }
                        ],
                    },
                },
            }
        ],
    }
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "result.json"
        with open(path, "w") as f:
            json.dump({"simulations": [sim, sim]}, f)
        rows = import_planner_results(path, "Ours", domain="retail", task_split_name="base")

    if len(rows) != 1:
        raise AssertionError(f"expected one imported row, got {len(rows)}")
    row = rows[0]
    if not row.get("official_success"):
        raise AssertionError(f"expected official_success=True, got {row}")
    if row.get("domain") != "retail" or row.get("task_split_name") != "base":
        raise AssertionError(f"expected imported domain/split metadata, got {row}")
    if row.get("gate_event_count") != 1:
        raise AssertionError(f"expected one gate event, got {row}")
    if row.get("gate_rejection_count") != 1:
        raise AssertionError(f"expected one gate rejection, got {row}")
    if row.get("gate_violation_breakdown", {}).get("MISSING_PARAMETER") != 1:
        raise AssertionError(f"expected missing parameter breakdown, got {row}")
    if row.get("gate_deterministic_repair_count") != 1:
        raise AssertionError(f"expected deterministic repair count, got {row}")
    if row.get("import_duplicate_pair_count") != 1:
        raise AssertionError(f"expected one duplicate pair count, got {row}")
    print("tau2 mechanism import smoke tests passed")


if __name__ == "__main__":
    main()
