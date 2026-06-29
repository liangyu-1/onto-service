#!/usr/bin/env python3
"""Convert reviewed ontology overlay records into Paper 1 gold functions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert reviewed ontology overlay JSONL to gold function JSONL.")
    parser.add_argument("--overlay", required=True, help="Reviewed ontology overlay JSONL.")
    parser.add_argument("--output", required=True, help="Output gold functions JSONL.")
    parser.add_argument("--include-draft", action="store_true", help="Also convert draft records. Use only for smoke tests.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = []
    skipped = 0
    for row in iter_jsonl(Path(args.overlay)):
        status = str(row.get("review_status", ""))
        if status != "reviewed" and not args.include_draft:
            skipped += 1
            continue
        rows.append(to_gold_function(row))

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
    print(json.dumps({"converted": len(rows), "skipped": skipped, "output": str(output)}, ensure_ascii=False, indent=2))


def to_gold_function(overlay: dict[str, Any]) -> dict[str, Any]:
    return {
        "function_id": str(overlay.get("candidate_function_id", "")),
        "endpoint_binding": overlay.get("endpoint_binding", {}),
        "operation_kind": str(overlay.get("operation_kind", "")),
        "description": evidence_claim(overlay),
        "bound_object_types": list(overlay.get("bound_object_types", [])),
        "inputs": [
            {
                "name": str(param.get("name", "")),
                "type": str(param.get("type", "string")),
                "semantic_role": str(param.get("semantic_role", "value")),
                "ontology_property": param.get("ontology_property"),
                "required": bool(param.get("required", False)),
            }
            for param in overlay.get("parameter_bindings", [])
        ],
        "outputs": [
            {
                "name": str(output.get("name", "")),
                "type": str(output.get("type", "object")),
                "semantic_role": str(output.get("semantic_role", "target_object")),
                "ontology_property": output.get("ontology_property"),
                "required": bool(output.get("required", False)),
            }
            for output in overlay.get("output_bindings", [])
        ],
        "preconditions": list(overlay.get("preconditions", [])),
        "effects": list(overlay.get("effects", [])),
        "error_contract": list(overlay.get("error_contract", [])),
        "evidence": list(overlay.get("evidence", [])),
    }


def evidence_claim(overlay: dict[str, Any]) -> str:
    evidence = overlay.get("evidence", [])
    if evidence and isinstance(evidence[0], dict):
        return str(evidence[0].get("claim", ""))
    return str(overlay.get("review_note", ""))


def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                yield json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc


if __name__ == "__main__":
    main()
