"""Function discovery from OpenAPI artifacts."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from .io_utils import load_json
from .schema import EndpointBinding, Evidence, FunctionCandidate, FunctionField


HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def discover_openapi_functions(path: Path) -> list[FunctionCandidate]:
    specs = list(_iter_openapi_specs(path))
    candidates: list[FunctionCandidate] = []
    for source_id, spec in specs:
        candidates.extend(_discover_from_spec(source_id, spec))
    if not candidates:
        raise ValueError(f"No OpenAPI operations discovered from {path}")
    return candidates


def _iter_openapi_specs(path: Path) -> Iterable[tuple[str, dict[str, Any]]]:
    if path.is_file():
        yield str(path), load_json(path)
        return
    if not path.is_dir():
        raise FileNotFoundError(path)
    for item in sorted(path.rglob("*.json")):
        yield str(item), load_json(item)


def _discover_from_spec(source_id: str, spec: dict[str, Any]) -> list[FunctionCandidate]:
    paths = spec.get("paths") or {}
    candidates: list[FunctionCandidate] = []
    for route, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            op_id = operation.get("operationId") or _operation_id(method, route)
            candidate = FunctionCandidate(
                function_id=str(op_id),
                endpoint_binding=EndpointBinding(method=method.upper(), path=str(route), operation_id=str(op_id)),
                operation_kind=_infer_operation_kind(method, str(route), str(op_id)),
                description=str(operation.get("summary") or operation.get("description") or ""),
                evidence_set=[
                    Evidence(
                        source_type="openapi",
                        source_id=source_id,
                        claim=f"{method.upper()} {route}",
                    )
                ],
            )
            candidate.inputs = _extract_parameters(operation, route)
            candidate.outputs = _extract_outputs(operation)
            candidate.error_contract = _extract_error_contract(operation)
            candidates.append(candidate)
    return candidates


def _operation_id(method: str, route: str) -> str:
    parts = [method.lower()] + [part.strip("{}") for part in route.split("/") if part]
    return "_".join(_normalize_token(part) for part in parts if part)


def _normalize_token(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9]+", "_", text)
    text = re.sub(r"([a-z])([A-Z])", r"\1_\2", text)
    return text.strip("_").lower()


def _infer_operation_kind(method: str, route: str, op_id: str) -> str:
    method = method.lower()
    text = f"{route} {op_id}".lower()
    if method == "get":
        return "read"
    if method == "post" and any(token in text for token in ("create", "add", "submit")):
        return "create"
    if method in {"put", "patch"} or any(token in text for token in ("update", "modify", "change")):
        return "update"
    if method == "delete" or any(token in text for token in ("delete", "cancel", "remove")):
        return "delete"
    return "external"


def _extract_parameters(operation: dict[str, Any], route: str) -> list[FunctionField]:
    fields: list[FunctionField] = []
    for param in operation.get("parameters", []) or []:
        if not isinstance(param, dict):
            continue
        schema = param.get("schema") or {}
        fields.append(
            FunctionField(
                name=str(param.get("name", "")),
                type=str(schema.get("type", "string")),
                semantic_role=_infer_role(str(param.get("name", ""))),
                required=bool(param.get("required", False) or f"{{{param.get('name')}}}" in route),
            )
        )
    request_body = operation.get("requestBody") or {}
    for name, field_type, required in _extract_schema_fields(request_body):
        fields.append(FunctionField(name=name, type=field_type, semantic_role=_infer_role(name), required=required))
    return _dedupe_fields(fields)


def _extract_outputs(operation: dict[str, Any]) -> list[FunctionField]:
    responses = operation.get("responses") or {}
    for status in ("200", "201", "202", "default"):
        response = responses.get(status)
        if not isinstance(response, dict):
            continue
        fields = [
            FunctionField(name=name, type=field_type, semantic_role=_infer_role(name), required=False)
            for name, field_type, _ in _extract_schema_fields(response)
        ]
        if fields:
            return _dedupe_fields(fields)
    return []


def _extract_schema_fields(container: dict[str, Any]) -> list[tuple[str, str, bool]]:
    content = container.get("content") or {}
    schemas: list[dict[str, Any]] = []
    for media in content.values():
        if isinstance(media, dict) and isinstance(media.get("schema"), dict):
            schemas.append(media["schema"])
    if isinstance(container.get("schema"), dict):
        schemas.append(container["schema"])

    fields: list[tuple[str, str, bool]] = []
    for schema in schemas:
        required = set(schema.get("required") or [])
        properties = schema.get("properties") or {}
        if isinstance(properties, dict):
            for name, prop in properties.items():
                field_type = str(prop.get("type", "object")) if isinstance(prop, dict) else "object"
                fields.append((str(name), field_type, str(name) in required))
    return fields


def _extract_error_contract(operation: dict[str, Any]) -> list[str]:
    errors = []
    responses = operation.get("responses") or {}
    for status, response in responses.items():
        try:
            code = int(status)
        except (TypeError, ValueError):
            continue
        if code >= 400:
            description = ""
            if isinstance(response, dict):
                description = str(response.get("description", ""))
            errors.append(f"{status}: {description}".strip())
    return errors


def _infer_role(name: str) -> str:
    low = name.lower()
    if low.endswith("_id") or low == "id":
        return "identifier"
    if any(token in low for token in ("status", "state")):
        return "state"
    if any(token in low for token in ("amount", "price", "quantity", "qty", "count")):
        return "measure"
    if any(token in low for token in ("date", "time", "timestamp")):
        return "time"
    return "value"


def _dedupe_fields(fields: list[FunctionField]) -> list[FunctionField]:
    seen: set[str] = set()
    deduped: list[FunctionField] = []
    for field in fields:
        key = field.name.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(field)
    return deduped
