"""Gold-label metrics for Paper 1 function-layer experiments."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .schema import FunctionCandidate


def compute_metrics(predicted: list[FunctionCandidate], gold: list[FunctionCandidate]) -> dict[str, Any]:
    pred_by_endpoint = {_endpoint_key(candidate): candidate for candidate in predicted}
    gold_by_endpoint = {_endpoint_key(candidate): candidate for candidate in gold}

    pred_keys = set(pred_by_endpoint)
    gold_keys = set(gold_by_endpoint)
    matched_keys = pred_keys & gold_keys

    metrics: dict[str, Any] = {
        "gold_available": True,
        "predicted_count": len(predicted),
        "gold_count": len(gold),
        "published_count": sum(candidate.status == "published" for candidate in predicted),
        "function_discovery": _prf(len(matched_keys), len(pred_keys), len(gold_keys)),
    }

    if matched_keys:
        metrics["target_object_accuracy"] = _mean(
            _set_overlap_exact(pred_by_endpoint[key].bound_object_types, gold_by_endpoint[key].bound_object_types)
            for key in matched_keys
        )
        metrics["parameter_role_f1"] = _mean(
            _field_f1(pred_by_endpoint[key], gold_by_endpoint[key], field="semantic_role") for key in matched_keys
        )
        metrics["property_link_f1"] = _mean(
            _field_f1(pred_by_endpoint[key], gold_by_endpoint[key], field="ontology_property") for key in matched_keys
        )
        metrics["precondition_f1"] = _mean(
            _list_f1(pred_by_endpoint[key].preconditions, gold_by_endpoint[key].preconditions) for key in matched_keys
        )
        metrics["effect_f1"] = _mean(
            _list_f1(pred_by_endpoint[key].effects, gold_by_endpoint[key].effects) for key in matched_keys
        )
        metrics["full_function_exact_match"] = _mean(
            _full_exact_match(pred_by_endpoint[key], gold_by_endpoint[key]) for key in matched_keys
        )
    else:
        metrics.update(
            {
                "target_object_accuracy": 0.0,
                "parameter_role_f1": 0.0,
                "property_link_f1": 0.0,
                "precondition_f1": 0.0,
                "effect_f1": 0.0,
                "full_function_exact_match": 0.0,
            }
        )

    published = [candidate for candidate in predicted if candidate.status == "published"]
    published_keys = {_endpoint_key(candidate) for candidate in published}
    wrong_published = len(published_keys - gold_keys)
    metrics["published_coverage"] = len(published_keys & gold_keys) / len(gold_keys) if gold_keys else 0.0
    metrics["published_error_rate"] = wrong_published / len(published_keys) if published_keys else 0.0
    return metrics


def _endpoint_key(candidate: FunctionCandidate) -> str:
    return f"{candidate.endpoint_binding.method.upper()} {candidate.endpoint_binding.path}"


def _prf(tp: int, predicted: int, gold: int) -> dict[str, float]:
    precision = tp / predicted if predicted else 0.0
    recall = tp / gold if gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def _mean(values) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _set_overlap_exact(pred: list[str], gold: list[str]) -> float:
    return 1.0 if set(pred) == set(gold) else 0.0


def _list_f1(pred: list[str], gold: list[str]) -> float:
    pred_counter = Counter(pred)
    gold_counter = Counter(gold)
    tp = sum((pred_counter & gold_counter).values())
    return _prf(tp, sum(pred_counter.values()), sum(gold_counter.values()))["f1"]


def _field_f1(pred: FunctionCandidate, gold: FunctionCandidate, field: str) -> float:
    pred_values = [getattr(item, field) for item in pred.inputs if getattr(item, field)]
    gold_values = [getattr(item, field) for item in gold.inputs if getattr(item, field)]
    return _list_f1(pred_values, gold_values)


def _full_exact_match(pred: FunctionCandidate, gold: FunctionCandidate) -> float:
    checks = [
        set(pred.bound_object_types) == set(gold.bound_object_types),
        {(f.name, f.semantic_role, f.ontology_property) for f in pred.inputs}
        == {(f.name, f.semantic_role, f.ontology_property) for f in gold.inputs},
        set(pred.preconditions) == set(gold.preconditions),
        set(pred.effects) == set(gold.effects),
    ]
    return 1.0 if all(checks) else 0.0
