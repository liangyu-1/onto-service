#!/usr/bin/env python3
"""Draft an object ontology from OpenAPI artifacts.

This creates a reviewable ontology candidate for Paper 1. The output is not a
gold ontology. It should be manually reviewed before benchmark annotation.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


HTTP_METHODS = {"get", "put", "post", "delete", "patch", "head", "options", "trace"}
STATE_WORDS = {
    "active",
    "approved",
    "archived",
    "blocked",
    "cancelled",
    "canceled",
    "closed",
    "completed",
    "confirmed",
    "created",
    "deleted",
    "disabled",
    "draft",
    "enabled",
    "failed",
    "inactive",
    "locked",
    "open",
    "paid",
    "pending",
    "rejected",
    "removed",
    "shipped",
    "submitted",
    "suspended",
    "updated",
}
ACTION_PATH_SEGMENTS = {
    "activate",
    "approve",
    "archive",
    "cancel",
    "close",
    "complete",
    "confirm",
    "create",
    "delete",
    "disable",
    "enable",
    "lock",
    "pay",
    "reject",
    "remove",
    "restore",
    "ship",
    "submit",
    "suspend",
    "unlock",
    "update",
}
LIFECYCLE_VERB_TO_STATE = {
    "cancel": "cancelled",
    "close": "closed",
    "complete": "completed",
    "confirm": "confirmed",
    "create": "created",
    "delete": "deleted",
    "disable": "disabled",
    "enable": "enabled",
    "lock": "locked",
    "pay": "paid",
    "reject": "rejected",
    "remove": "removed",
    "ship": "shipped",
    "submit": "submitted",
    "suspend": "suspended",
    "update": "updated",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Draft an object ontology from OpenAPI JSON files.")
    parser.add_argument("--openapi", required=True, help="OpenAPI JSON file or directory.")
    parser.add_argument("--output", required=True, help="Output ontology JSON.")
    parser.add_argument("--name", default="paper1_object_ontology_draft")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_path = Path(args.openapi)
    specs = list(iter_openapi_specs(source_path))
    if not specs:
        raise FileNotFoundError(f"No OpenAPI JSON files found: {source_path}")

    builder = OntologyDraftBuilder(name=args.name)
    for source_id, spec in specs:
        builder.add_openapi(source_id, spec)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        json.dump(builder.to_dict(), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({"object_type_count": len(builder.objects), "output": str(output)}, ensure_ascii=False, indent=2))


class OntologyDraftBuilder:
    def __init__(self, name: str) -> None:
        self.name = name
        self.objects: dict[str, dict[str, Any]] = {}
        self.relations: dict[tuple[str, str, str], dict[str, Any]] = {}
        self.source_files: list[str] = []

    def add_openapi(self, source_id: str, spec: dict[str, Any]) -> None:
        self.source_files.append(source_id)
        self._add_component_schemas(source_id, spec)
        self._add_path_and_operation_evidence(source_id, spec)

    def _add_component_schemas(self, source_id: str, spec: dict[str, Any]) -> None:
        schemas = spec.get("components", {}).get("schemas", {})
        if not isinstance(schemas, dict):
            return
        for schema_name, schema in schemas.items():
            if not isinstance(schema, dict):
                continue
            object_id = pascal_case(str(schema_name))
            obj = self._ensure_object(
                object_id,
                evidence={
                    "source_type": "openapi_schema",
                    "source_reference": f"{source_id}#/components/schemas/{schema_name}",
                    "claim": f"Schema object {schema_name}",
                },
            )
            obj["aliases"].update(alias_candidates(schema_name))
            description = str(schema.get("description", ""))
            if description:
                obj["evidence"].append(
                    {
                        "source_type": "openapi_schema",
                        "source_reference": f"{source_id}#/components/schemas/{schema_name}",
                        "claim": description,
                    }
                )
                obj["aliases"].update(nounish_aliases(description))
            self._add_schema_properties(source_id, object_id, schema_name, schema)

    def _add_schema_properties(self, source_id: str, object_id: str, schema_name: str, schema: dict[str, Any]) -> None:
        obj = self._ensure_object(object_id)
        required = set(schema.get("required") or [])
        properties = schema.get("properties") or {}
        if not isinstance(properties, dict):
            return
        for prop_name, prop in properties.items():
            if not isinstance(prop, dict):
                prop = {}
            prop_type, ref_object = property_type(prop)
            property_record = {
                "id": str(prop_name),
                "type": prop_type,
                "aliases": sorted(alias_candidates(str(prop_name))),
                "required": str(prop_name) in required,
                "evidence": [
                    {
                        "source_type": "openapi_schema_property",
                        "source_reference": f"{source_id}#/components/schemas/{schema_name}/properties/{prop_name}",
                        "claim": f"{schema_name}.{prop_name}",
                    }
                ],
            }
            if prop.get("description"):
                property_record["evidence"].append(
                    {
                        "source_type": "openapi_schema_property",
                        "source_reference": f"{source_id}#/components/schemas/{schema_name}/properties/{prop_name}",
                        "claim": str(prop["description"]),
                    }
                )
            obj["properties"][str(prop_name)] = merge_property(obj["properties"].get(str(prop_name)), property_record)

            if is_state_property(str(prop_name)):
                for state in state_candidates_from_property(prop):
                    add_state(obj, state, source_id, f"#/components/schemas/{schema_name}/properties/{prop_name}")
            if ref_object:
                target = pascal_case(ref_object)
                self._ensure_object(target)
                self._ensure_relation(
                    source=object_id,
                    relation=str(prop_name),
                    target=target,
                    evidence={
                        "source_type": "openapi_schema_property",
                        "source_reference": f"{source_id}#/components/schemas/{schema_name}/properties/{prop_name}",
                        "claim": f"{object_id}.{prop_name} references {target}",
                    },
                )

    def _add_path_and_operation_evidence(self, source_id: str, spec: dict[str, Any]) -> None:
        for path, path_item in (spec.get("paths") or {}).items():
            if not isinstance(path_item, dict):
                continue
            path_objects = objects_from_path(str(path))
            for object_id in path_objects:
                obj = self._ensure_object(
                    object_id,
                    evidence={
                        "source_type": "openapi_path",
                        "source_reference": f"{source_id}#/paths/{json_pointer_escape(str(path))}",
                        "claim": str(path),
                    },
                )
                obj["aliases"].update(alias_candidates(object_id))
            for parent, child in zip(path_objects, path_objects[1:]):
                self._ensure_relation(
                    source=parent,
                    relation=f"has_{snake_case(child)}",
                    target=child,
                    evidence={
                        "source_type": "openapi_path",
                        "source_reference": f"{source_id}#/paths/{json_pointer_escape(str(path))}",
                        "claim": f"Nested path relation {parent} -> {child}",
                    },
                )
            for method, operation in path_item.items():
                if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                    continue
                operation_id = str(operation.get("operationId") or "")
                summary = str(operation.get("summary") or operation.get("description") or "")
                operation_text = f"{path} {operation_id} {summary} {' '.join(extract_error_contract(operation))}"
                mentioned_objects = set(path_objects)
                mentioned_objects.update(object_mentions(operation_text, self.objects))
                for object_id in mentioned_objects:
                    obj = self._ensure_object(object_id)
                    obj["evidence"].append(
                        {
                            "source_type": "openapi_operation",
                            "source_reference": f"{source_id}#/paths/{json_pointer_escape(str(path))}/{method.lower()}",
                            "claim": summary or f"{method.upper()} {path}",
                        }
                    )
                    for state in state_candidates_from_text(operation_text):
                        add_state(obj, state, source_id, f"#/paths/{json_pointer_escape(str(path))}/{method.lower()}")

    def _ensure_object(self, object_id: str, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
        if object_id not in self.objects:
            self.objects[object_id] = {
                "id": object_id,
                "aliases": set(alias_candidates(object_id)),
                "properties": {},
                "states": {},
                "evidence": [],
                "review_status": "draft",
            }
        if evidence:
            self.objects[object_id]["evidence"].append(evidence)
        return self.objects[object_id]

    def _ensure_relation(self, source: str, relation: str, target: str, evidence: dict[str, Any]) -> None:
        key = (source, relation, target)
        if key not in self.relations:
            self.relations[key] = {
                "source": source,
                "relation": relation,
                "target": target,
                "evidence": [],
                "review_status": "draft",
            }
        self.relations[key]["evidence"].append(evidence)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": {
                "name": self.name,
                "kind": "openapi_derived_object_ontology_draft",
                "warning": "Auto-generated draft. Review object boundaries, aliases, states, and relations before use as gold ontology.",
                "source_files": self.source_files,
            },
            "object_types": [finalize_object(obj) for obj in sorted(self.objects.values(), key=lambda row: row["id"])],
            "relations": [relation for _, relation in sorted(self.relations.items())],
        }


def iter_openapi_specs(path: Path) -> Iterable[tuple[str, dict[str, Any]]]:
    if path.is_file():
        yield str(path), load_json(path)
        return
    if not path.is_dir():
        return
    for item in sorted(path.rglob("*.json")):
        try:
            spec = load_json(item)
        except json.JSONDecodeError:
            continue
        if isinstance(spec, dict) and "paths" in spec:
            yield str(item), spec


def finalize_object(obj: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": obj["id"],
        "aliases": sorted(obj["aliases"]),
        "properties": sorted(obj["properties"].values(), key=lambda row: row["id"]),
        "states": sorted(obj["states"].values(), key=lambda row: row["id"]),
        "evidence": obj["evidence"],
        "review_status": obj["review_status"],
    }


def merge_property(existing: dict[str, Any] | None, new: dict[str, Any]) -> dict[str, Any]:
    if not existing:
        return new
    existing["aliases"] = sorted(set(existing.get("aliases", [])) | set(new.get("aliases", [])))
    existing["required"] = bool(existing.get("required")) or bool(new.get("required"))
    existing["evidence"].extend(new.get("evidence", []))
    if existing.get("type") == "object" and new.get("type") != "object":
        existing["type"] = new["type"]
    return existing


def add_state(obj: dict[str, Any], state: str, source_id: str, pointer: str) -> None:
    state = normalize_state(state)
    if not state:
        return
    if state not in obj["states"]:
        obj["states"][state] = {
            "id": state,
            "evidence": [],
            "review_status": "draft",
        }
    obj["states"][state]["evidence"].append(
        {
            "source_type": "openapi_state_candidate",
            "source_reference": f"{source_id}{pointer}",
            "claim": state,
        }
    )


def property_type(prop: dict[str, Any]) -> tuple[str, str | None]:
    if "$ref" in prop:
        return "object", str(prop["$ref"]).rsplit("/", 1)[-1]
    if prop.get("type") == "array":
        items = prop.get("items") or {}
        if isinstance(items, dict) and "$ref" in items:
            return "array", str(items["$ref"]).rsplit("/", 1)[-1]
        return "array", None
    return str(prop.get("type", "object")), None


def is_state_property(name: str) -> bool:
    return normalize(name) in {"state", "status", "stage", "lifecycle_state", "lifecycle_status"}


def state_candidates_from_property(prop: dict[str, Any]) -> set[str]:
    states = set()
    enum_values = prop.get("enum") or []
    if isinstance(enum_values, list):
        states.update(str(value) for value in enum_values if isinstance(value, (str, int)))
    description = str(prop.get("description", ""))
    states.update(state_candidates_from_text(description))
    return states


def state_candidates_from_text(text: str) -> set[str]:
    normalized = normalize(text)
    tokens = set(normalized.split("_"))
    states = {word for word in STATE_WORDS if word in tokens}
    for verb, state in LIFECYCLE_VERB_TO_STATE.items():
        if verb in tokens or f"{verb}ed" in tokens:
            states.add(state)
    return states


def objects_from_path(path: str) -> list[str]:
    objects = []
    for segment in path.split("/"):
        if not segment or segment.startswith("{"):
            continue
        clean = segment.strip("{}")
        if clean.startswith("v") and clean[1:].isdigit():
            continue
        if normalize(singularize(clean)) in ACTION_PATH_SEGMENTS:
            continue
        object_id = pascal_case(singularize(clean))
        if object_id and object_id not in objects:
            objects.append(object_id)
    return objects


def object_mentions(text: str, objects: dict[str, dict[str, Any]]) -> set[str]:
    normalized_text = normalize(text)
    found = set()
    for object_id, obj in objects.items():
        candidates = {normalize(object_id)}
        candidates.update(normalize(alias) for alias in obj.get("aliases", []))
        if any(candidate and candidate in normalized_text for candidate in candidates):
            found.add(object_id)
    return found


def extract_error_contract(operation: dict[str, Any]) -> list[str]:
    errors = []
    for status, response in (operation.get("responses") or {}).items():
        try:
            code = int(status)
        except (TypeError, ValueError):
            continue
        if code >= 400 and isinstance(response, dict):
            errors.append(str(response.get("description", "")))
    return errors


def alias_candidates(name: str) -> set[str]:
    snake = snake_case(name)
    words = snake.replace("_", " ")
    return {name, snake, words, singularize(words)}


def nounish_aliases(text: str) -> set[str]:
    aliases = set()
    for match in re.findall(r"\b[A-Z][A-Za-z0-9]*(?:\s+[A-Z][A-Za-z0-9]*)?\b", text):
        if len(match) > 2:
            aliases.add(match)
    return aliases


def singularize(text: str) -> str:
    parts = text.split()
    if len(parts) > 1:
        return " ".join([*parts[:-1], singularize(parts[-1])])
    if text.endswith("ies") and len(text) > 3:
        return text[:-3] + "y"
    if text.endswith("ses"):
        return text[:-2]
    if text.endswith("s") and not text.endswith("ss") and len(text) > 3:
        return text[:-1]
    return text


def pascal_case(text: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", text.replace("_", " "))
    return "".join(word[:1].upper() + word[1:] for word in words) or "UnknownObject"


def snake_case(text: str) -> str:
    text = re.sub(r"([a-z])([A-Z])", r"\1_\2", text)
    text = re.sub(r"[^A-Za-z0-9]+", "_", text)
    return text.strip("_").lower() or "unknown"


def normalize(text: str) -> str:
    return snake_case(text).lower()


def normalize_state(text: str) -> str:
    return normalize(str(text))


def json_pointer_escape(path: str) -> str:
    return path.replace("~", "~0").replace("/", "~1")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


if __name__ == "__main__":
    main()
