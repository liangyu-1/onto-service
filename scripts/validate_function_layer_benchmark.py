#!/usr/bin/env python3
"""Validate Paper 1 Function Layer benchmark files.

This is a structural validator. It does not decide whether the annotation is
semantically correct; it checks that OpenAPI operations, ontology bindings,
gold functions, and optional traces are mutually consistent.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


HTTP_METHODS = {"get", "put", "post", "delete", "patch", "head", "options", "trace"}
OPERATION_KINDS = {"read", "create", "update", "delete", "compute", "external"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Paper 1 Function Layer benchmark files.")
    parser.add_argument("--openapi", required=True, help="OpenAPI JSON file.")
    parser.add_argument("--ontology", required=True, help="Ontology JSON file.")
    parser.add_argument("--overlay", help="Optional ontology overlay JSONL.")
    parser.add_argument("--gold", required=True, help="Gold functions JSONL.")
    parser.add_argument("--traces", help="Optional traces JSONL.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    openapi = load_json(Path(args.openapi))
    ontology = load_json(Path(args.ontology))
    overlay_records = list(iter_jsonl(Path(args.overlay))) if args.overlay else []
    gold_functions = list(iter_jsonl(Path(args.gold)))
    traces = list(iter_jsonl(Path(args.traces))) if args.traces else []

    operation_index = collect_openapi_operations(openapi)
    object_ids, property_ids = collect_ontology_ids(ontology)
    trace_index = {(str(row.get("method", "")).upper(), str(row.get("path", ""))) for row in traces}

    errors: list[dict[str, Any]] = []
    for row_index, overlay in enumerate(overlay_records, start=1):
        errors.extend(validate_overlay(row_index, overlay, operation_index, object_ids, property_ids))
    seen_functions: set[str] = set()
    for row_index, function in enumerate(gold_functions, start=1):
        errors.extend(validate_function(row_index, function, operation_index, object_ids, property_ids, trace_index))
        function_id = str(function.get("function_id", ""))
        if function_id in seen_functions:
            errors.append(error(row_index, f"duplicate_function_id:{function_id}"))
        seen_functions.add(function_id)

    payload = {
        "ok": not errors,
        "openapi_operation_count": len(operation_index),
        "overlay_count": len(overlay_records),
        "gold_function_count": len(gold_functions),
        "trace_count": len(traces),
        "error_count": len(errors),
        "errors": errors[:200],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


def validate_overlay(
    row_index: int,
    overlay: dict[str, Any],
    operation_index: set[tuple[str, str, str]],
    object_ids: set[str],
    property_ids: set[str],
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for required in (
        "endpoint_binding",
        "candidate_function_id",
        "operation_kind",
        "bound_object_types",
        "parameter_bindings",
        "output_bindings",
        "review_status",
        "evidence",
    ):
        if required not in overlay:
            errors.append(error(row_index, f"overlay_missing_field:{required}"))

    binding = overlay.get("endpoint_binding", {})
    method = str(binding.get("method", "")).upper()
    path = str(binding.get("path", ""))
    operation_id = str(binding.get("operation_id", ""))
    if (method, path, operation_id) not in operation_index:
        # Fallback: many APIs.guru specs lack operationId; accept (method, path) match.
        if not any(m == method and p == path for m, p, _ in operation_index):
            errors.append(error(row_index, f"overlay_operation_not_in_openapi:{method} {path} {operation_id}"))

    operation_kind = str(overlay.get("operation_kind", ""))
    if operation_kind not in OPERATION_KINDS:
        errors.append(error(row_index, f"overlay_invalid_operation_kind:{operation_kind}"))

    for object_id in overlay.get("bound_object_types", []):
        if str(object_id) not in object_ids:
            errors.append(error(row_index, f"overlay_unknown_object_type:{object_id}"))

    for group in ("parameter_bindings", "output_bindings"):
        for binding_row in overlay.get(group, []):
            ontology_property = binding_row.get("ontology_property")
            if not ontology_property:
                continue
            ontology_property = str(ontology_property)
            if "." in ontology_property and ontology_property not in property_ids:
                errors.append(error(row_index, f"overlay_unknown_property:{ontology_property}"))
            if "." not in ontology_property and ontology_property not in object_ids:
                errors.append(error(row_index, f"overlay_unknown_object_binding:{ontology_property}"))

    review_status = str(overlay.get("review_status", ""))
    if review_status not in {"draft", "reviewed", "rejected"}:
        errors.append(error(row_index, f"overlay_invalid_review_status:{review_status}"))
    return errors


def validate_function(
    row_index: int,
    function: dict[str, Any],
    operation_index: set[tuple[str, str, str]],
    object_ids: set[str],
    property_ids: set[str],
    trace_index: set[tuple[str, str]],
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for required in ("function_id", "endpoint_binding", "operation_kind", "bound_object_types", "inputs", "outputs"):
        if required not in function:
            errors.append(error(row_index, f"missing_field:{required}"))

    binding = function.get("endpoint_binding", {})
    method = str(binding.get("method", "")).upper()
    path = str(binding.get("path", ""))
    operation_id = str(binding.get("operation_id", ""))
    if (method, path, operation_id) not in operation_index:
        if not any(m == method and p == path for m, p, _ in operation_index):
            errors.append(error(row_index, f"operation_not_in_openapi:{method} {path} {operation_id}"))
    if trace_index and (method, path) not in trace_index:
        errors.append(error(row_index, f"operation_without_trace:{method} {path}"))

    operation_kind = str(function.get("operation_kind", ""))
    if operation_kind not in OPERATION_KINDS:
        errors.append(error(row_index, f"invalid_operation_kind:{operation_kind}"))

    for object_id in function.get("bound_object_types", []):
        if str(object_id) not in object_ids:
            errors.append(error(row_index, f"unknown_object_type:{object_id}"))

    for group in ("inputs", "outputs"):
        for field in function.get(group, []):
            ontology_property = field.get("ontology_property")
            if not ontology_property:
                continue
            ontology_property = str(ontology_property)
            if "." in ontology_property and ontology_property not in property_ids:
                errors.append(error(row_index, f"unknown_property:{ontology_property}"))
            if "." not in ontology_property and ontology_property not in object_ids:
                errors.append(error(row_index, f"unknown_output_object:{ontology_property}"))

    if not function.get("evidence"):
        errors.append(error(row_index, "missing_evidence"))
    return errors


def collect_openapi_operations(openapi: dict[str, Any]) -> set[tuple[str, str, str]]:
    operations = set()
    for path, path_item in openapi.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            operations.add((method.upper(), str(path), str(operation.get("operationId", ""))))
    return operations


def collect_ontology_ids(ontology: dict[str, Any]) -> tuple[set[str], set[str]]:
    object_ids = set()
    property_ids = set()
    for obj in ontology.get("object_types", []):
        object_id = str(obj.get("id", ""))
        if not object_id:
            continue
        object_ids.add(object_id)
        for prop in obj.get("properties", []):
            prop_id = str(prop.get("id", ""))
            if prop_id:
                property_ids.add(f"{object_id}.{prop_id}")
    return object_ids, property_ids


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


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


def error(row_index: int, message: str) -> dict[str, Any]:
    return {"row": row_index, "error": message}


if __name__ == "__main__":
    main()
