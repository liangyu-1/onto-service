"""Ontology alignment for function candidates."""

from __future__ import annotations

import re

from .schema import FunctionCandidate, FunctionField, ObjectLayer, ObjectType, OntologyProperty


def align_candidates(candidates: list[FunctionCandidate], ontology: ObjectLayer) -> list[FunctionCandidate]:
    for candidate in candidates:
        object_scores = [(obj.id, _object_score(candidate, obj)) for obj in ontology.object_types]
        object_scores.sort(key=lambda item: item[1], reverse=True)
        candidate.bound_object_types = [obj_id for obj_id, score in object_scores[:2] if score > 0]
        for field in candidate.inputs:
            field.ontology_property = _align_field(field, ontology, candidate.bound_object_types)
        for field in candidate.outputs:
            field.ontology_property = _align_field(field, ontology, candidate.bound_object_types)
        _infer_state_semantics(candidate, ontology)
    return candidates


def _object_score(candidate: FunctionCandidate, obj: ObjectType) -> float:
    haystack = " ".join(
        [
            candidate.function_id,
            candidate.endpoint_binding.path,
            candidate.description,
            " ".join(field.name for field in candidate.inputs),
            " ".join(field.name for field in candidate.outputs),
        ]
    ).lower()
    names = [obj.id, *obj.aliases]
    score = 0.0
    for name in names:
        token = _norm(name)
        if not token:
            continue
        if token in _norm(haystack):
            score += 2.0
        elif token.rstrip("s") in _norm(haystack):
            score += 1.0
    return score


def _align_field(field: FunctionField, ontology: ObjectLayer, preferred_objects: list[str]) -> str | None:
    candidates: list[tuple[str, float]] = []
    field_norm = _norm(field.name)
    for obj in ontology.object_types:
        object_bonus = 0.5 if obj.id in preferred_objects else 0.0
        for prop in obj.properties:
            score = _property_score(field_norm, prop) + object_bonus
            if score > 0:
                candidates.append((f"{obj.id}.{prop.id}", score))
    if not candidates:
        for obj in ontology.object_types:
            if field.semantic_role == "identifier" and _norm(obj.id) in field_norm:
                return f"{obj.id}.{field.name}"
        return None
    candidates.sort(key=lambda item: item[1], reverse=True)
    return candidates[0][0]


def _property_score(field_norm: str, prop: OntologyProperty) -> float:
    names = [prop.id, *prop.aliases]
    score = 0.0
    for name in names:
        prop_norm = _norm(name)
        if not prop_norm:
            continue
        if field_norm == prop_norm:
            score += 3.0
        elif field_norm.endswith(prop_norm) or prop_norm.endswith(field_norm):
            score += 1.5
        elif prop_norm in field_norm:
            score += 1.0
    return score


def _infer_state_semantics(candidate: FunctionCandidate, ontology: ObjectLayer) -> None:
    text = _norm(" ".join([candidate.function_id, candidate.description, candidate.endpoint_binding.path]))
    for obj in ontology.object_types:
        if obj.id not in candidate.bound_object_types:
            continue
        for state in obj.states:
            state_norm = _norm(state)
            if state_norm and state_norm in text:
                candidate.preconditions.append(f"{obj.id}.state == {state}")
        if candidate.operation_kind in {"create", "update", "delete"}:
            candidate.effects.append(f"{obj.id}.state changes")


def _norm(text: str) -> str:
    text = re.sub(r"([a-z])([A-Z])", r"\1_\2", text)
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
