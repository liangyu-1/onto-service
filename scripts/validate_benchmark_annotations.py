#!/usr/bin/env python3
"""Validate gold benchmark annotation files.

This checks structural consistency only. It does not judge semantic quality.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate ontology workflow benchmark annotations.")
    parser.add_argument("--annotations", required=True, help="Gold workflow JSONL.")
    parser.add_argument("--ontology", required=True, help="Ontology JSON.")
    parser.add_argument("--functions", required=True, help="Function Layer JSONL.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ontology = load_json(Path(args.ontology))
    functions = list(iter_jsonl(Path(args.functions)))
    annotations = list(iter_jsonl(Path(args.annotations)))

    object_ids = {str(obj.get("id")) for obj in ontology.get("object_types", []) if obj.get("id")}
    function_ids = {str(function.get("function_id")) for function in functions if function.get("function_id")}

    errors = []
    for row_index, skill in enumerate(annotations, start=1):
        errors.extend(validate_skill(row_index, skill, object_ids, function_ids))

    if errors:
        print(json.dumps({"ok": False, "error_count": len(errors), "errors": errors[:200]}, ensure_ascii=False, indent=2))
        raise SystemExit(1)
    print(json.dumps({"ok": True, "annotation_count": len(annotations)}, ensure_ascii=False, indent=2))


def validate_skill(
    row_index: int,
    skill: dict[str, Any],
    object_ids: set[str],
    function_ids: set[str],
) -> list[dict[str, Any]]:
    errors = []
    node_ids = {str(node.get("node_id")) for node in skill.get("nodes", []) if node.get("node_id")}
    variable_types = {
        str(var.get("name")): str(var.get("type"))
        for var in skill.get("object_variables", [])
        if var.get("name") and var.get("type")
    }
    for required in ("skill_id", "source_id", "nodes"):
        if required not in skill:
            errors.append(error(row_index, f"missing_field:{required}"))
    for node in skill.get("nodes", []):
        node_id = str(node.get("node_id", ""))
        node_type = str(node.get("node_type", ""))
        function_id = node.get("function_id")
        if not node_id:
            errors.append(error(row_index, "node_missing_id"))
        if node_type == "OntologyFunctionCall" and not function_id:
            errors.append(error(row_index, f"node_missing_function:{node_id}"))
        if function_id and str(function_id) not in function_ids:
            errors.append(error(row_index, f"unknown_function:{function_id}"))
        for var_name in node.get("object_variables", []):
            var_type = variable_types.get(str(var_name))
            if not var_type:
                errors.append(error(row_index, f"unknown_variable:{var_name}"))
            elif object_ids and var_type not in object_ids:
                errors.append(error(row_index, f"unknown_object_type:{var_type}"))
    for edge_group in ("control_edges", "dataflow_edges", "exception_paths"):
        for edge in skill.get(edge_group, []):
            source = str(edge.get("source", ""))
            target = str(edge.get("target", ""))
            if "." not in source and source not in node_ids:
                errors.append(error(row_index, f"{edge_group}:unknown_source:{source}"))
            if "." not in target and target not in node_ids:
                errors.append(error(row_index, f"{edge_group}:unknown_target:{target}"))
    return errors


def error(row_index: int, message: str) -> dict[str, Any]:
    return {"row": row_index, "error": message}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if stripped:
                try:
                    yield json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc


if __name__ == "__main__":
    main()
