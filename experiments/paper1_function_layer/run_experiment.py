#!/usr/bin/env python3
"""Run Paper 1 function-layer construction and evaluation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.alignment import align_candidates
from src.contract_generation import generate_contracts
from src.discovery import discover_openapi_functions
from src.io_utils import dump_json, dump_jsonl, load_gold_functions, load_ontology, load_traces
from src.metrics import compute_metrics
from src.publisher import publish_candidates
from src.validation import validate_candidates


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Construct ontology-bound atomic functions from OpenAPI artifacts."
    )
    parser.add_argument("--openapi", required=True, help="OpenAPI JSON file or directory.")
    parser.add_argument("--ontology", required=True, help="Object-layer ontology JSON.")
    parser.add_argument("--gold", help="Optional JSONL gold functions.")
    parser.add_argument("--traces", help="Optional JSONL execution traces or replay observations.")
    parser.add_argument("--output-dir", default="outputs/paper1_function_layer")
    parser.add_argument("--publish-threshold", type=float, default=0.72)
    parser.add_argument("--abstain-threshold", type=float, default=0.45)
    parser.add_argument("--llm-base-url", help="OpenAI-compatible base URL for full-method contract generation.")
    parser.add_argument("--llm-model", help="Model name for full-method contract generation.")
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY", help="Environment variable containing the API key.")
    parser.add_argument("--llm-timeout", type=float, default=60.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ontology = load_ontology(Path(args.ontology))
    traces = load_traces(Path(args.traces)) if args.traces else []
    gold = load_gold_functions(Path(args.gold)) if args.gold else []

    discovered = discover_openapi_functions(Path(args.openapi))
    aligned = align_candidates(discovered, ontology)
    generated = generate_contracts(
        aligned,
        ontology,
        base_url=args.llm_base_url,
        model=args.llm_model,
        api_key_env=args.api_key_env,
        timeout=args.llm_timeout,
    )
    validated, validation_report = validate_candidates(generated, ontology, traces)
    published = publish_candidates(
        validated,
        publish_threshold=args.publish_threshold,
        abstain_threshold=args.abstain_threshold,
    )

    dump_jsonl(output_dir / "all_candidates.jsonl", [candidate.to_dict() for candidate in published])
    dump_jsonl(
        output_dir / "published_functions.jsonl",
        [candidate.to_dict() for candidate in published if candidate.status == "published"],
    )
    dump_json(output_dir / "validation_report.json", validation_report)

    metrics = compute_metrics(published, gold) if gold else {"gold_available": False}
    dump_json(output_dir / "metrics.json", metrics)

    print(json.dumps({"candidates": len(published), "published": sum(c.status == "published" for c in published), "output_dir": str(output_dir)}, indent=2))


if __name__ == "__main__":
    main()
