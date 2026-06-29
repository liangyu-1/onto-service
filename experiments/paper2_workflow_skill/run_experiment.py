#!/usr/bin/env python3
"""Run Paper 2 ontology workflow skill induction."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.generator import generate_workflows
from src.io_utils import dump_json, dump_jsonl, iter_jsonl, load_documents, load_function_layer, load_ontology
from src.metrics import compute_metrics
from src.validation import validate_workflows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Induce ontology Workflow Skills from procedural documents.")
    parser.add_argument("--documents", required=True, help="JSONL procedural documents.")
    parser.add_argument("--ontology", required=True, help="Object ontology JSON.")
    parser.add_argument("--function-layer", required=True, help="JSONL Function Layer.")
    parser.add_argument("--gold-workflows", help="Optional JSONL gold OntologyWorkflowSkill annotations.")
    parser.add_argument("--output-dir", default="outputs/paper2_workflow_skill")
    parser.add_argument("--max-docs", type=int, default=0)
    parser.add_argument("--llm-base-url", help="OpenAI-compatible base URL.")
    parser.add_argument("--llm-model", help="Model id, e.g. glm-5.2.")
    parser.add_argument("--api-key-env", default="GLM_API_KEY")
    parser.add_argument("--llm-timeout", type=float, default=60.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    documents = load_documents(Path(args.documents), max_docs=args.max_docs)
    ontology = load_ontology(Path(args.ontology))
    functions = load_function_layer(Path(args.function_layer))
    gold_workflows = list(iter_jsonl(Path(args.gold_workflows))) if args.gold_workflows else None

    workflows = generate_workflows(
        documents=documents,
        ontology=ontology,
        functions=functions,
        base_url=args.llm_base_url,
        model=args.llm_model,
        api_key_env=args.api_key_env,
        timeout=args.llm_timeout,
    )
    validation_report = validate_workflows(workflows, ontology, functions)
    metrics = compute_metrics(workflows, documents, validation_report, gold_workflows=gold_workflows)

    dump_jsonl(output_dir / "workflow_skills.jsonl", [workflow.to_dict() for workflow in workflows])
    dump_json(output_dir / "validation_report.json", validation_report)
    dump_json(output_dir / "metrics.json", metrics)
    print(json.dumps({"documents": len(documents), "workflows": len(workflows), "output_dir": str(output_dir)}, indent=2))


if __name__ == "__main__":
    main()
