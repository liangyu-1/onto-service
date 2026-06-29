"""Automatic validation for ontology function candidates."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .schema import Evidence, FunctionCandidate, ObjectLayer


def validate_candidates(
    candidates: list[FunctionCandidate],
    ontology: ObjectLayer,
    traces: list[dict[str, Any]],
) -> tuple[list[FunctionCandidate], dict[str, Any]]:
    object_ids = {obj.id for obj in ontology.object_types}
    property_ids = set(ontology.property_index())
    trace_index = _trace_index(traces)
    error_counts: Counter[str] = Counter()

    for candidate in candidates:
        candidate.validation_errors.clear()
        for obj_id in candidate.bound_object_types:
            if obj_id not in object_ids:
                candidate.validation_errors.append(f"unknown_object:{obj_id}")
        if not candidate.bound_object_types:
            candidate.validation_errors.append("missing_object_binding")
        for field in [*candidate.inputs, *candidate.outputs]:
            if field.ontology_property and "." in field.ontology_property and field.ontology_property not in property_ids:
                candidate.validation_errors.append(f"unknown_property:{field.ontology_property}")
            if field.required and not field.name:
                candidate.validation_errors.append("required_field_without_name")
        if not candidate.endpoint_binding.method or not candidate.endpoint_binding.path:
            candidate.validation_errors.append("missing_endpoint_binding")
        _validate_trace_support(candidate, trace_index)
        error_counts.update(candidate.validation_errors)
        candidate.confidence = _score_candidate(candidate)

    report = {
        "candidate_count": len(candidates),
        "error_counts": dict(error_counts),
        "trace_available": bool(traces),
        "trace_supported": sum("trace_supported" in {e.claim for e in c.evidence_set} for c in candidates),
    }
    return candidates, report


def _trace_index(traces: list[dict[str, Any]]) -> set[tuple[str, str]]:
    index: set[tuple[str, str]] = set()
    for row in traces:
        method = str(row.get("method", "")).upper()
        path = str(row.get("path", ""))
        if method and path:
            index.add((method, path))
    return index


def _validate_trace_support(candidate: FunctionCandidate, trace_index: set[tuple[str, str]]) -> None:
    if not trace_index:
        return
    key = (candidate.endpoint_binding.method.upper(), candidate.endpoint_binding.path)
    if key not in trace_index:
        candidate.validation_errors.append("no_trace_support")
        return
    candidate.evidence_set.append(
        Evidence(
            source_type="trace",
            source_id=f"{key[0]} {key[1]}",
            claim="trace_supported",
            confidence=1.0,
        )
    )


def _score_candidate(candidate: FunctionCandidate) -> float:
    score = 0.25
    if candidate.bound_object_types:
        score += 0.2
    if candidate.inputs:
        score += 0.1
    if candidate.outputs:
        score += 0.1
    if candidate.effects or candidate.operation_kind == "read":
        score += 0.1
    if candidate.error_contract:
        score += 0.05
    if candidate.evidence_set:
        score += 0.1
    score -= min(0.4, 0.08 * len(candidate.validation_errors))
    return max(0.0, min(1.0, score))
