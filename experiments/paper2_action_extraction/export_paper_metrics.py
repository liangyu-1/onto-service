#!/usr/bin/env python3
"""Export paper-ready metrics from paper2 results."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any, Dict


def format_latex_row(method: str, metrics: Dict[str, float]) -> str:
    """Format a LaTeX table row."""
    return (
        f"{method} & "
        f"{metrics.get('action_mention_f1_mean', 0):.3f} & "
        f"{metrics.get('action_type_accuracy_mean', 0):.3f} & "
        f"{metrics.get('target_grounding_accuracy_mean', 0):.3f} & "
        f"{metrics.get('parameter_grounding_f1_mean', 0):.3f} & "
        f"{metrics.get('evidence_span_f1_mean', 0):.3f} & "
        f"{metrics.get('control_flow_f1_mean', 0):.3f} & "
        f"{metrics.get('validation_pass_rate_mean', 0):.3f} \\\\"
    )


def format_md_row(method: str, metrics: Dict[str, float]) -> str:
    """Format a Markdown table row."""
    return (
        f"| {method:<15} | "
        f"{metrics.get('action_mention_f1_mean', 0):>8.3f} | "
        f"{metrics.get('action_type_accuracy_mean', 0):>8.3f} | "
        f"{metrics.get('target_grounding_accuracy_mean', 0):>8.3f} | "
        f"{metrics.get('parameter_grounding_f1_mean', 0):>8.3f} | "
        f"{metrics.get('evidence_span_f1_mean', 0):>8.3f} | "
        f"{metrics.get('control_flow_f1_mean', 0):>8.3f} | "
        f"{metrics.get('validation_pass_rate_mean', 0):>8.3f} |"
    )


def export(results_dir: pathlib.Path, json_out: pathlib.Path, md_out: pathlib.Path):
    combined_path = results_dir / "combined_results.json"
    if not combined_path.exists():
        print(f"No combined_results.json found in {results_dir}")
        sys.exit(1)

    with open(combined_path) as f:
        data = json.load(f)

    evaluations = data.get("evaluations", {})
    methods = list(evaluations.keys())

    # JSON export
    json_data = {
        "run_id": data.get("run_id", ""),
        "methods": {},
    }
    for method, ev in evaluations.items():
        json_data["methods"][method] = {
            "action_mention_f1": ev.get("action_mention_f1_mean", 0),
            "action_type_accuracy": ev.get("action_type_accuracy_mean", 0),
            "target_grounding_accuracy": ev.get("target_grounding_accuracy_mean", 0),
            "parameter_grounding_f1": ev.get("parameter_grounding_f1_mean", 0),
            "evidence_span_f1": ev.get("evidence_span_f1_mean", 0),
            "control_flow_f1": ev.get("control_flow_f1_mean", 0),
            "validation_pass_rate": ev.get("validation_pass_rate_mean", 0),
        }

    if json_out:
        with open(json_out, "w") as f:
            json.dump(json_data, f, indent=2)
        print(f"JSON metrics → {json_out}")

    # Markdown export
    if md_out:
        lines = [
            "# Paper 2: Ontology-Grounded Action Extraction Metrics",
            "",
            "| Method          | ActionF1 | TypeAcc | TargetAcc | ParamF1 | EvidF1 | FlowF1 | ValPass |",
            "|-----------------|----------|---------|-----------|---------|--------|--------|---------|",
        ]
        for method in methods:
            lines.append(format_md_row(method, evaluations[method]))
        lines.append("")
        with open(md_out, "w") as f:
            f.write("\n".join(lines))
        print(f"Markdown table → {md_out}")

    # LaTeX print
    print("\n% LaTeX table rows")
    print("\\begin{tabular}{lccccccc}")
    print("\\toprule")
    print("Method & Action F1 & Type Acc & Target Acc & Param F1 & Evid F1 & Flow F1 & ValPass \\\\")
    print("\\midrule")
    for method in methods:
        print(format_latex_row(method, evaluations[method]))
    print("\\bottomrule")
    print("\\end{tabular}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("results_dir", type=pathlib.Path)
    parser.add_argument("--json-out", type=pathlib.Path)
    parser.add_argument("--md-out", type=pathlib.Path)
    args = parser.parse_args()

    export(args.results_dir, args.json_out, args.md_out)


if __name__ == "__main__":
    main()
