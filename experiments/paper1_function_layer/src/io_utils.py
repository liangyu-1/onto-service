"""File IO helpers for Paper 1 experiments."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .schema import EndpointBinding, FunctionCandidate, FunctionField, ObjectLayer, ObjectType, OntologyProperty


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def dump_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                yield json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc


def load_ontology(path: Path) -> ObjectLayer:
    raw = load_json(path)
    objects = []
    for obj in raw.get("object_types", []):
        props = tuple(
            OntologyProperty(
                id=str(prop["id"]),
                type=str(prop.get("type", "string")),
                aliases=tuple(str(alias) for alias in prop.get("aliases", [])),
            )
            for prop in obj.get("properties", [])
        )
        objects.append(
            ObjectType(
                id=str(obj["id"]),
                aliases=tuple(str(alias) for alias in obj.get("aliases", [])),
                properties=props,
                states=tuple(str(state) for state in obj.get("states", [])),
            )
        )
    if not objects:
        raise ValueError(f"Ontology has no object_types: {path}")
    return ObjectLayer(object_types=tuple(objects))


def load_gold_functions(path: Path) -> list[FunctionCandidate]:
    return [_candidate_from_dict(row) for row in iter_jsonl(path)]


def load_traces(path: Path) -> list[dict[str, Any]]:
    return list(iter_jsonl(path))


def _candidate_from_dict(row: dict[str, Any]) -> FunctionCandidate:
    endpoint = row.get("endpoint_binding") or {}
    candidate = FunctionCandidate(
        function_id=str(row["function_id"]),
        endpoint_binding=EndpointBinding(
            method=str(endpoint.get("method", "")).upper(),
            path=str(endpoint.get("path", "")),
            operation_id=endpoint.get("operation_id"),
        ),
        operation_kind=str(row.get("operation_kind", "")),
        description=str(row.get("description", "")),
        bound_object_types=list(row.get("bound_object_types", [])),
        preconditions=list(row.get("preconditions", [])),
        effects=list(row.get("effects", [])),
        error_contract=list(row.get("error_contract", [])),
        confidence=float(row.get("confidence", 1.0)),
        status=str(row.get("status", "published")),
    )
    candidate.inputs = [_field_from_dict(field) for field in row.get("inputs", [])]
    candidate.outputs = [_field_from_dict(field) for field in row.get("outputs", [])]
    return candidate


def _field_from_dict(row: dict[str, Any]) -> FunctionField:
    return FunctionField(
        name=str(row["name"]),
        type=str(row.get("type", "string")),
        semantic_role=str(row.get("semantic_role", "value")),
        ontology_property=row.get("ontology_property"),
        required=bool(row.get("required", False)),
    )
