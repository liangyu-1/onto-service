#!/usr/bin/env python3
"""Run, import, analyze, and validate official tau2 paired experiments."""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys
from typing import List


BASE_DIR = pathlib.Path(__file__).resolve().parent


def run_command(cmd: List[str], dry_run: bool) -> None:
    print("\n$ " + " ".join(cmd), flush=True)
    if dry_run:
        return
    subprocess.run(cmd, check=True)


def maybe_add(cmd: List[str], flag: str, value) -> None:
    if value is None:
        return
    if isinstance(value, list):
        if value:
            cmd.append(flag)
            cmd.extend(str(v) for v in value)
        return
    cmd.extend([flag, str(value)])


def tau2_agent_cmd(args, agent_kind: str, save_to: str) -> List[str]:
    cmd = [
        sys.executable,
        str(BASE_DIR / "tau2_ontology_agent.py"),
        "--domain",
        args.domain,
        "--agent-kind",
        agent_kind,
        "--agent-model",
        args.agent_model,
        "--agent-base-url",
        args.agent_base_url,
        "--api-key",
        args.api_key,
        "--user-llm",
        args.user_llm,
        "--task-split-name",
        args.task_split_name,
        "--num-trials",
        str(args.num_trials),
        "--max-concurrency",
        str(args.max_concurrency),
        "--max-steps",
        str(args.max_steps),
        "--save-to",
        save_to,
    ]
    maybe_add(cmd, "--num-tasks", args.num_tasks)
    maybe_add(cmd, "--task-ids", args.task_ids)
    return cmd


def preflight_cmd(args) -> List[str]:
    cmd = [
        sys.executable,
        str(BASE_DIR / "preflight_official_tau2.py"),
        "--agent-model",
        args.agent_model,
        "--agent-base-url",
        args.agent_base_url,
        "--api-key",
        args.api_key,
    ]
    if args.skip_tau2_import_check:
        cmd.append("--skip-tau2-import-check")
    if args.skip_model_check:
        cmd.append("--skip-model-check")
    return cmd


def resolve_results_path(explicit_path: str | None, simulations_dir: pathlib.Path, save_to: str) -> pathlib.Path:
    if explicit_path:
        return pathlib.Path(explicit_path)
    candidates = [
        simulations_dir / save_to,
        pathlib.Path(save_to),
        pathlib.Path(f"{save_to}.json"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Official paired tau2 experiment pipeline.")
    parser.add_argument("--domain", default="retail")
    parser.add_argument("--agent-model", default="gemma4-31b")
    parser.add_argument("--agent-base-url", default="http://172.16.22.79:9999/v1")
    parser.add_argument("--api-key", default="EMPTY")
    parser.add_argument("--user-llm", required=True)
    parser.add_argument("--task-split-name", default="base")
    parser.add_argument("--num-trials", type=int, default=1)
    parser.add_argument("--num-tasks", type=int, default=None)
    parser.add_argument("--task-ids", nargs="*", default=None)
    parser.add_argument("--max-concurrency", type=int, default=1)
    parser.add_argument("--max-steps", type=int, default=200)
    parser.add_argument("--schema-save-to", default="schema_baseline_retail")
    parser.add_argument("--ontology-prompt-save-to", default="ontology_prompt_retail")
    parser.add_argument("--ontology-lite-save-to", default="ontology_lite_retail")
    parser.add_argument("--ontology-save-to", default="ontology_guided_retail")
    parser.add_argument("--simulations-dir", default="data/simulations")
    parser.add_argument("--schema-results-path", default=None)
    parser.add_argument("--ontology-prompt-results-path", default=None)
    parser.add_argument("--ontology-lite-results-path", default=None)
    parser.add_argument("--ontology-results-path", default=None)
    parser.add_argument(
        "--combined-output",
        default=str(BASE_DIR / "results_official_tau2/combined.json"),
    )
    parser.add_argument(
        "--report-output",
        default=str(BASE_DIR / "results_official_tau2/official_report.md"),
    )
    parser.add_argument("--skip-run", action="store_true", help="Only import/analyze/validate existing result paths.")
    parser.add_argument("--skip-preflight", action="store_true", help="Do not run official-run preflight checks.")
    parser.add_argument("--skip-tau2-import-check", action="store_true", help="Preflight: skip tau2 import checks.")
    parser.add_argument("--skip-model-check", action="store_true", help="Preflight: skip vLLM/OpenAI-compatible model check.")
    parser.add_argument(
        "--run-ablations",
        action="store_true",
        help="Also run/import OntologyPrompt and OntologyLite ablations.",
    )
    parser.add_argument("--skip-validate", action="store_true")
    parser.add_argument(
        "--skip-gate-trace-validation",
        action="store_true",
        help="Do not require ontology gate traces in the proposed planner results.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.skip_run:
        if not args.skip_preflight:
            run_command(preflight_cmd(args), args.dry_run)
        run_command(tau2_agent_cmd(args, "schema", args.schema_save_to), args.dry_run)
        if args.run_ablations:
            run_command(tau2_agent_cmd(args, "ontology_prompt", args.ontology_prompt_save_to), args.dry_run)
            run_command(tau2_agent_cmd(args, "ontology_lite", args.ontology_lite_save_to), args.dry_run)
        run_command(tau2_agent_cmd(args, "ontology", args.ontology_save_to), args.dry_run)

    simulations_dir = pathlib.Path(args.simulations_dir)
    schema_path = resolve_results_path(args.schema_results_path, simulations_dir, args.schema_save_to)
    ontology_prompt_path = resolve_results_path(
        args.ontology_prompt_results_path,
        simulations_dir,
        args.ontology_prompt_save_to,
    )
    ontology_lite_path = resolve_results_path(
        args.ontology_lite_results_path,
        simulations_dir,
        args.ontology_lite_save_to,
    )
    ontology_path = resolve_results_path(args.ontology_results_path, simulations_dir, args.ontology_save_to)

    import_cmd = [
        sys.executable,
        str(BASE_DIR / "import_tau2_results.py"),
        "--left-path",
        str(schema_path),
        "--left-name",
        "Schema-Only",
        "--right-path",
        str(ontology_path),
        "--right-name",
        "Ours",
        "--domain",
        args.domain,
        "--task-split-name",
        args.task_split_name,
        "--output",
        args.combined_output,
    ]
    if args.run_ablations:
        import_cmd.extend([
            "--extra",
            f"OntologyPrompt={ontology_prompt_path}",
            "--extra",
            f"OntologyLite={ontology_lite_path}",
        ])
    run_command(import_cmd, args.dry_run)

    analyze_cmd = [
        sys.executable,
        str(BASE_DIR / "analyze_results.py"),
        args.combined_output,
    ]
    run_command(analyze_cmd, args.dry_run)

    report_cmd = [
        sys.executable,
        str(BASE_DIR / "report_official_results.py"),
        args.combined_output,
        "--output-md",
        args.report_output,
    ]
    run_command(report_cmd, args.dry_run)

    if not args.skip_validate:
        validate_cmd = [
            sys.executable,
            str(BASE_DIR / "validate_official_results.py"),
            args.combined_output,
        ]
        if not args.skip_gate_trace_validation:
            validate_cmd.append("--require-gate-trace")
        run_command(validate_cmd, args.dry_run)


if __name__ == "__main__":
    main()
