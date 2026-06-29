#!/usr/bin/env python3
"""Draft Paper 1 ontology overlay records from OpenAPI and an object ontology.

The output is intentionally marked as `draft`. It is a review aid, not gold.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


HTTP_METHODS = {"get", "put", "post", "delete", "patch", "head", "options", "trace"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Draft ontology overlay records from OpenAPI.")
    parser.add_argument("--openapi", required=True, help="OpenAPI JSON file.")
    parser.add_argument("--ontology", required=True, help="Object ontology JSON file.")
    parser.add_argument("--output", required=True, help="Output JSONL draft overlay file.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    openapi_path = Path(args.openapi)
    openapi = load_json(openapi_path)
    ontology = load_json(Path(args.ontology))
    object_index = build_object_index(ontology)
    property_index = build_property_index(ontology)

    rows = []
    for path, method, operation in iter_operations(openapi):
        rows.append(draft_overlay(openapi_path.name, openapi, path, method, operation, object_index, property_index))

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
    print(json.dumps({"draft_overlay_count": len(rows), "output": str(output)}, ensure_ascii=False, indent=2))


def draft_overlay(
    source_name: str,
    openapi: dict[str, Any],
    path: str,
    method: str,
    operation: dict[str, Any],
    object_index: dict[str, str],
    property_index: dict[str, str],
) -> dict[str, Any]:
    operation_id = str(operation.get("operationId") or operation_id_from_path(method, path))
    description = str(operation.get("summary") or operation.get("description") or "")
    text = f"{path} {operation_id} {description}"
    bound_objects = infer_objects(text, object_index)
    parameters = draft_parameter_bindings(openapi, operation, path, bound_objects, property_index)
    outputs = draft_output_bindings(openapi, operation, bound_objects)
    return {
        "overlay_id": canonical_id(source_name, operation_id),
        "endpoint_binding": {
            "method": method.upper(),
            "path": path,
            "operation_id": operation_id,
        },
        "candidate_function_id": snake_case(operation_id),
        "operation_kind": infer_operation_kind(method, path, operation_id),
        "bound_object_types": bound_objects,
        "parameter_bindings": parameters,
        "output_bindings": outputs,
        "preconditions": [],
        "effects": [],
        "error_contract": extract_error_contract(operation),
        "review_status": "draft",
        "review_note": "Auto-drafted from OpenAPI. Manually review object bindings, preconditions, and effects.",
        "evidence": [
            {
                "source_type": "openapi",
                "source_reference": f"{source_name}#/paths/{json_pointer_escape(path)}/{method.lower()}",
                "claim": description or f"{method.upper()} {path}",
            }
        ],
    }


def draft_parameter_bindings(
    openapi: dict[str, Any],
    operation: dict[str, Any],
    path: str,
    bound_objects: list[str],
    property_index: dict[str, str],
) -> list[dict[str, Any]]:
    rows = []
    for param in operation.get("parameters", []) or []:
        if not isinstance(param, dict):
            continue
        name = str(param.get("name", ""))
        schema = param.get("schema") or {}
        rows.append(
            {
                "name": name,
                "location": str(param.get("in", "")),
                "type": str(schema.get("type", "string")),
                "semantic_role": infer_role(name),
                "ontology_property": infer_property(name, bound_objects, property_index),
                "required": bool(param.get("required", False) or f"{{{name}}}" in path),
                "evidence": f"{param.get('in', '')} parameter {name}",
            }
        )
    for name, field_type, required, ref_object in extract_request_body_fields(openapi, operation):
        ontology_property = infer_property(name, bound_objects, property_index)
        if not ontology_property and ref_object in bound_objects:
            ontology_property = ref_object
        rows.append(
            {
                "name": name,
                "location": "requestBody",
                "type": field_type,
                "semantic_role": infer_role(name),
                "ontology_property": ontology_property,
                "required": required,
                "evidence": f"requestBody field {name}",
            }
        )
    return dedupe_by_name(rows)


def draft_output_bindings(openapi: dict[str, Any], operation: dict[str, Any], bound_objects: list[str]) -> list[dict[str, Any]]:
    schema_ref = first_success_schema_ref(operation)
    if schema_ref:
        object_name = schema_ref.rsplit("/", 1)[-1]
        return [
            {
                "name": snake_case(object_name),
                "type": "object",
                "ontology_property": object_name if object_name in bound_objects else None,
                "evidence": f"success response schema {schema_ref}",
            }
        ]
    return []


def build_object_index(ontology: dict[str, Any]) -> dict[str, str]:
    index = {}
    for obj in ontology.get("object_types", []):
        object_id = str(obj.get("id", ""))
        if not object_id:
            continue
        index[normalize(object_id)] = object_id
        for alias in obj.get("aliases", []):
            index[normalize(str(alias))] = object_id
    return index


def build_property_index(ontology: dict[str, Any]) -> dict[str, str]:
    index = {}
    for obj in ontology.get("object_types", []):
        object_id = str(obj.get("id", ""))
        for prop in obj.get("properties", []):
            prop_id = str(prop.get("id", ""))
            if prop_id:
                index[normalize(prop_id)] = f"{object_id}.{prop_id}"
            for alias in prop.get("aliases", []):
                index[normalize(str(alias))] = f"{object_id}.{prop_id}"
    return index


def infer_objects(text: str, object_index: dict[str, str]) -> list[str]:
    normalized_text = normalize(text)
    found = []
    for key, object_id in object_index.items():
        if key and key in normalized_text and object_id not in found:
            found.append(object_id)
    return found


def infer_property(name: str, bound_objects: list[str], property_index: dict[str, str]) -> str | None:
    normalized_name = normalize(name)
    if normalized_name in property_index:
        prop = property_index[normalized_name]
        if not bound_objects or prop.split(".", 1)[0] in bound_objects:
            return prop
    if normalized_name.endswith("_id"):
        object_hint = normalized_name.removesuffix("_id")
        for obj in bound_objects:
            if normalize(obj) == object_hint:
                return f"{obj}.{name}"
    return None


def iter_operations(openapi: dict[str, Any]):
    for path, path_item in openapi.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() in HTTP_METHODS and isinstance(operation, dict):
                yield str(path), method.lower(), operation


def extract_request_body_fields(openapi: dict[str, Any], operation: dict[str, Any]) -> list[tuple[str, str, bool, str | None]]:
    request_body = operation.get("requestBody") or {}
    return extract_schema_fields(openapi, request_body)


def extract_schema_fields(openapi: dict[str, Any], container: dict[str, Any]) -> list[tuple[str, str, bool, str | None]]:
    content = container.get("content") or {}
    schemas = []
    for media in content.values():
        if isinstance(media, dict) and isinstance(media.get("schema"), dict):
            schemas.append(media["schema"])
    fields = []
    for schema in schemas:
        ref_object = None
        if "$ref" in schema:
            ref_object = str(schema["$ref"]).rsplit("/", 1)[-1]
            schema = resolve_ref(openapi, str(schema["$ref"])) or schema
        required = set(schema.get("required") or [])
        properties = schema.get("properties") or {}
        if isinstance(properties, dict):
            for name, prop in properties.items():
                prop_ref = str(prop.get("$ref", "")).rsplit("/", 1)[-1] if isinstance(prop, dict) and prop.get("$ref") else None
                field_type = str(prop.get("type", "object")) if isinstance(prop, dict) else "object"
                fields.append((str(name), field_type, str(name) in required, prop_ref or ref_object))
        elif ref_object:
            fields.append((snake_case(ref_object), "object", bool(container.get("required", False)), ref_object))
    return fields


def resolve_ref(openapi: dict[str, Any], ref: str) -> dict[str, Any] | None:
    if not ref.startswith("#/"):
        return None
    current: Any = openapi
    for part in ref[2:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current if isinstance(current, dict) else None


def first_success_schema_ref(operation: dict[str, Any]) -> str | None:
    responses = operation.get("responses") or {}
    for status in ("200", "201", "202", "default"):
        response = responses.get(status)
        if not isinstance(response, dict):
            continue
        content = response.get("content") or {}
        for media in content.values():
            schema = media.get("schema") if isinstance(media, dict) else None
            if isinstance(schema, dict) and "$ref" in schema:
                return str(schema["$ref"])
    return None


def extract_error_contract(operation: dict[str, Any]) -> list[str]:
    errors = []
    for status, response in (operation.get("responses") or {}).items():
        try:
            code = int(status)
        except (TypeError, ValueError):
            continue
        if code >= 400:
            description = str(response.get("description", "")) if isinstance(response, dict) else ""
            errors.append(f"{status}: {description}".strip())
    return errors


def infer_operation_kind(method: str, path: str, operation_id: str) -> str:
    text = f"{method} {path} {operation_id}".lower()
    if method == "get":
        return "read"
    if method in {"put", "patch"} or any(token in text for token in ("update", "modify", "change")):
        return "update"
    if method == "delete" or any(token in text for token in ("delete", "cancel", "remove")):
        return "delete"
    if method == "post" and any(token in text for token in ("create", "add", "submit")):
        return "create"
    return "external"


def infer_role(name: str) -> str:
    low = name.lower()
    if low.endswith("_id") or low == "id":
        return "identifier"
    if any(token in low for token in ("state", "status")):
        return "state"
    if any(token in low for token in ("reason", "approval", "policy", "permission")):
        return "policy"
    if any(token in low for token in ("amount", "price", "quantity", "count")):
        return "measure"
    if any(token in low for token in ("date", "time", "timestamp")):
        return "time"
    return "payload"


def dedupe_by_name(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    deduped = []
    for row in rows:
        key = (row.get("location"), row.get("name"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def operation_id_from_path(method: str, path: str) -> str:
    return "_".join([method.lower(), *[part.strip("{}") for part in path.split("/") if part]])


def canonical_id(source_name: str, operation_id: str) -> str:
    return f"{Path(source_name).stem}.{snake_case(operation_id)}"


def snake_case(text: str) -> str:
    text = re.sub(r"([a-z])([A-Z])", r"\1_\2", text)
    text = re.sub(r"[^A-Za-z0-9]+", "_", text)
    return text.strip("_").lower() or "unknown"


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def json_pointer_escape(path: str) -> str:
    return path.replace("~", "~0").replace("/", "~1")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


if __name__ == "__main__":
    main()
