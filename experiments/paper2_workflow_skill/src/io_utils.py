"""IO helpers for Paper 2 experiments."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .schema import DocumentRecord, FunctionSpec


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


def load_documents(path: Path, max_docs: int = 0) -> list[DocumentRecord]:
    rows = []
    for row in iter_jsonl(path):
        rows.append(
            DocumentRecord(
                dataset=str(row.get("dataset", "")),
                source_id=str(row.get("source_id", "")),
                domain=str(row.get("domain", "")),
                text=str(row.get("text", "")),
                actions=list(row.get("actions", [])),
                metadata=dict(row.get("metadata", {})),
            )
        )
        if max_docs and len(rows) >= max_docs:
            break
    if not rows:
        raise ValueError(f"No documents loaded from {path}")
    return rows


def load_ontology(path: Path) -> dict[str, Any]:
    ontology = load_json(path)
    if not isinstance(ontology, dict):
        raise ValueError(f"Ontology must be a JSON object: {path}")
    return ontology


def load_function_layer(path: Path) -> list[FunctionSpec]:
    if not path.exists():
        raise FileNotFoundError(
            f"Function Layer not found: {path}. Use Paper 1 output or a curated Function Layer."
        )
    functions = []
    for row in iter_jsonl(path):
        functions.append(
            FunctionSpec(
                function_id=str(row.get("function_id") or row.get("id") or ""),
                description=str(row.get("description", "")),
                bound_object_types=tuple(row.get("bound_object_types", [])),
                inputs=tuple(row.get("inputs", [])),
                outputs=tuple(row.get("outputs", [])),
                preconditions=tuple(row.get("preconditions", [])),
                effects=tuple(row.get("effects", [])),
            )
        )
    functions = [function for function in functions if function.function_id]
    if not functions:
        raise ValueError(f"Function Layer has no functions: {path}")
    return functions
