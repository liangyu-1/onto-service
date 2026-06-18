#!/usr/bin/env python3
"""Generate paper-ready tables from official tau2/tau3 combined results."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any, Dict, List

BASE_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from analyze_results import (  # noqa: E402
    claim_readiness,
    gate_mechanism_summary,
    is_official_result,
    mcnemar_test,
    metric_value,
    paired_by_task_id,
    paired_effect,
    pair_coverage,
    task_cluster_effect,
    violation_breakdown,
)


DEFAULT_PAIRS = [
    ("Schema-Only", "OntologyPrompt"),
    ("OntologyPrompt", "OntologyLite"),
    ("OntologyLite", "Ours"),
    ("Schema-Only", "Ours"),
]


def load_combined(path: pathlib.Path) -> Dict[str, List[Dict[str, Any]]]:
    with open(path) as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("combined result must be a planner-name -> rows JSON object")
    return data


def planner_summary(data: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    rows = []
    for planner, results in data.items():
        valid = [r for r in results if isinstance(r, dict) and "error" not in r]
        if not valid:
            continue
        success = sum(1 for r in valid if metric_value(r, "paper_task_performance"))
        unique_tasks = len({str(r.get("task_id")) for r in valid if r.get("task_id") is not None})
        official = all(is_official_result(r) for r in valid)
        domains = sorted({str(r.get("domain")) for r in valid if r.get("domain")})
        task_splits = sorted({str(r.get("task_split_name")) for r in valid if r.get("task_split_name")})
        gate = gate_mechanism_summary(valid)
        duplicate_pairs = max((int(r.get("import_duplicate_pair_count", 0) or 0) for r in valid), default=0)
        rows.append({
            "planner": planner,
            "n": len(valid),
            "unique_tasks": unique_tasks,
            "official_success": success,
            "official_success_rate": success / len(valid),
            "official_result": official,
            "domains": domains,
            "task_split_names": task_splits,
            "import_duplicate_pair_count": duplicate_pairs,
            **gate,
        })
    return rows


def pair_summary(data: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    rows = []
    for left, right in DEFAULT_PAIRS:
        if left not in data or right not in data:
            continue
        effect = paired_effect(data[left], data[right], "paper_task_performance")
        sig = mcnemar_test(data[left], data[right], "paper_task_performance")
        task_effect = task_cluster_effect(data[left], data[right], "paper_task_performance")
        coverage = pair_coverage(data[left], data[right])
        rows.append({
            "left": left,
            "right": right,
            "paired_simulations": sig["paired_n"],
            "left_unpaired_n": coverage["left_unpaired_n"],
            "right_unpaired_n": coverage["right_unpaired_n"],
            "left_rate": effect.get("schema_rate", 0),
            "right_rate": effect.get("ours_rate", 0),
            "delta": effect.get("delta", 0),
            "delta_ci_95": effect.get("delta_ci_95", (0.0, 0.0)),
            "mcnemar_p": sig["p_value"],
            "task_n": task_effect["n_tasks"],
            "task_delta": task_effect["delta"],
            "task_delta_ci_95": task_effect["delta_ci_95"],
            "task_sign_p": task_effect["sign_test"]["p_value"],
            "ours_improves": sig["b_ours_improves"],
            "ours_worsens": sig["c_ours_worsens"],
        })
    return rows


def mechanism_summary(data: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    rows = []
    for planner, results in data.items():
        valid = [r for r in results if isinstance(r, dict) and "error" not in r]
        gate = gate_mechanism_summary(valid)
        if not gate["gate_event_count"] and not gate["gate_rejection_count"]:
            continue
        rows.append({
            "planner": planner,
            **gate,
            "violation_breakdown": violation_breakdown(valid),
        })
    return rows


def hard_cases(data: Dict[str, List[Dict[str, Any]]], left: str, right: str, limit: int) -> List[Dict[str, Any]]:
    if left not in data or right not in data:
        return []
    cases = []
    for left_row, right_row in paired_by_task_id(data[left], data[right]):
        left_ok = metric_value(left_row, "paper_task_performance")
        right_ok = metric_value(right_row, "paper_task_performance")
        if left_ok == right_ok:
            continue
        cases.append({
            "task_id": right_row.get("task_id") or left_row.get("task_id"),
            "pair_id": right_row.get("pair_id") or left_row.get("pair_id"),
            "left_success": left_ok,
            "right_success": right_ok,
            "right_gate_rejections": right_row.get("gate_rejection_count", 0),
            "right_gate_violations": right_row.get("gate_violation_breakdown", {}),
        })
    return cases[:limit]


def pct(value: float) -> str:
    return f"{100 * value:.1f}%"


def fmt_ci(ci: Any) -> str:
    if not isinstance(ci, (list, tuple)) or len(ci) != 2:
        return ""
    return f"[{100 * ci[0]:.1f}, {100 * ci[1]:.1f}]"


def markdown_table(headers: List[str], rows: List[List[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(lines)


def build_report(data: Dict[str, List[Dict[str, Any]]], source: pathlib.Path, hard_case_limit: int) -> Dict[str, Any]:
    return {
        "source": str(source),
        "planner_summary": planner_summary(data),
        "pair_summary": pair_summary(data),
        "mechanism_summary": mechanism_summary(data),
        "claim_readiness": claim_readiness(data, "Schema-Only", "Ours"),
        "hard_cases": hard_cases(data, "Schema-Only", "Ours", hard_case_limit),
    }


def render_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Official tau2 Result Report",
        "",
        f"Source: `{report['source']}`",
        "",
        "## Planner Summary",
        "",
    ]
    lines.append(markdown_table(
        ["Planner", "N", "Tasks", "Domain", "Split", "Official", "Success", "Duplicate Pairs", "Gate Events", "Gate Rejects", "Repair Attempts"],
        [
            [
                row["planner"],
                row["n"],
                row["unique_tasks"],
                ",".join(row["domains"]) or "unknown",
                ",".join(row["task_split_names"]) or "unknown",
                row["official_result"],
                f"{row['official_success']}/{row['n']} ({pct(row['official_success_rate'])})",
                row["import_duplicate_pair_count"],
                row["gate_event_count"],
                row["gate_rejection_count"],
                row["gate_repair_attempt_count"],
            ]
            for row in report["planner_summary"]
        ],
    ))
    lines.extend(["", "## Paired Comparisons", ""])
    lines.append(markdown_table(
        ["Comparison", "N", "Unpaired L/R", "Task N", "Left", "Right", "Delta", "CI95", "McNemar p", "Task Delta", "Task CI95", "Task p"],
        [
            [
                f"{row['left']} -> {row['right']}",
                row["paired_simulations"],
                f"{row['left_unpaired_n']}/{row['right_unpaired_n']}",
                row["task_n"],
                pct(row["left_rate"]),
                pct(row["right_rate"]),
                pct(row["delta"]),
                fmt_ci(row["delta_ci_95"]),
                row["mcnemar_p"],
                pct(row["task_delta"]),
                fmt_ci(row["task_delta_ci_95"]),
                row["task_sign_p"],
            ]
            for row in report["pair_summary"]
        ],
    ))
    lines.extend(["", "## Ontology Gate Mechanism", ""])
    if report["mechanism_summary"]:
        lines.append(markdown_table(
            ["Planner", "Gate Events", "Rejects", "Repair Attempts", "Deterministic Repairs", "Simulations With Rejects", "Violation Breakdown"],
            [
                [
                    row["planner"],
                    row["gate_event_count"],
                    row["gate_rejection_count"],
                    row["gate_repair_attempt_count"],
                    row["gate_deterministic_repair_count"],
                    row["simulations_with_gate_rejections"],
                    json.dumps(row["violation_breakdown"], ensure_ascii=False, sort_keys=True),
                ]
                for row in report["mechanism_summary"]
            ],
        ))
    else:
        lines.append("No ontology gate traces found.")

    readiness = report["claim_readiness"]
    lines.extend(["", "## Claim Readiness", ""])
    lines.append(f"Ready: `{readiness.get('ready')}`")
    lines.append(f"Metric: `{readiness.get('metric', 'unknown')}`")
    if "delta" in readiness:
        task_effect = readiness["task_cluster_effect"]
        lines.append(f"Simulation delta: {pct(readiness['delta'])}, McNemar p={readiness['mcnemar']['p_value']}")
        lines.append(
            f"Task-cluster delta: {pct(task_effect['delta'])}, "
            f"task sign p={task_effect['sign_test']['p_value']}"
        )
    if readiness.get("reasons"):
        lines.append("")
        lines.append("Blocking reasons:")
        for reason in readiness["reasons"]:
            lines.append(f"- {reason}")

    lines.extend(["", "## Discordant Cases", ""])
    if report["hard_cases"]:
        lines.append(markdown_table(
            ["Task", "Pair", "Schema Success", "Ours Success", "Ours Gate Rejects", "Ours Gate Violations"],
            [
                [
                    row["task_id"],
                    row["pair_id"],
                    row["left_success"],
                    row["right_success"],
                    row["right_gate_rejections"],
                    json.dumps(row["right_gate_violations"], ensure_ascii=False, sort_keys=True),
                ]
                for row in report["hard_cases"]
            ],
        ))
    else:
        lines.append("No discordant cases found.")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate paper-ready report from official tau2 combined JSON.")
    parser.add_argument("combined_json")
    parser.add_argument("--output-md", default=str(BASE_DIR / "results_official_tau2/official_report.md"))
    parser.add_argument("--output-json", default=None)
    parser.add_argument("--hard-case-limit", type=int, default=20)
    args = parser.parse_args()

    source = pathlib.Path(args.combined_json)
    data = load_combined(source)
    report = build_report(data, source, args.hard_case_limit)

    output_md = pathlib.Path(args.output_md)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(render_markdown(report), encoding="utf-8")
    print(f"Wrote {output_md}")

    if args.output_json:
        output_json = pathlib.Path(args.output_json)
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Wrote {output_json}")


if __name__ == "__main__":
    main()
