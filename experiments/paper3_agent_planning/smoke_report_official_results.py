#!/usr/bin/env python3
"""Smoke test paper-ready report generation."""
from __future__ import annotations

import json
import pathlib
import tempfile

from smoke_task_cluster_stats import official_row
from report_official_results import build_report, load_combined, render_markdown


def build_data() -> dict:
    data = {"Schema-Only": [], "OntologyPrompt": [], "OntologyLite": [], "Ours": []}
    for idx in range(40):
        task_id = f"task_{idx:03d}"
        data["Schema-Only"].append(official_row(task_id, 0, "Schema-Only", False))
        data["OntologyPrompt"].append(official_row(task_id, 0, "OntologyPrompt", idx >= 35))
        data["OntologyLite"].append(official_row(task_id, 0, "OntologyLite", idx >= 30, gate=True))
        ours = official_row(task_id, 0, "Ours", True, gate=True)
        ours["gate_rejection_count"] = 1
        ours["gate_repair_attempt_count"] = 1
        ours["gate_violation_breakdown"] = {"MISSING_PARAMETER": 1}
        data["Ours"].append(ours)
    return data


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        combined = pathlib.Path(tmp) / "combined.json"
        combined.write_text(json.dumps(build_data()), encoding="utf-8")
        data = load_combined(combined)
        report = build_report(data, combined, hard_case_limit=5)
        markdown = render_markdown(report)

    required = [
        "## Planner Summary",
        "## Paired Comparisons",
        "Schema-Only -> Ours",
        "## Ontology Gate Mechanism",
        "## Claim Readiness",
    ]
    for text in required:
        if text not in markdown:
            raise AssertionError(f"missing report section/text: {text}")
    if not report["claim_readiness"]["ready"]:
        raise AssertionError(f"synthetic all-improve report should be ready: {report['claim_readiness']['reasons']}")
    print("official report smoke tests passed")


if __name__ == "__main__":
    main()
