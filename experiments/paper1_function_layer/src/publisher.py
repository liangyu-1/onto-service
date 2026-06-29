"""Autonomous publication policy for Function Layer candidates."""

from __future__ import annotations

from .schema import FunctionCandidate


CRITICAL_ERRORS = {
    "missing_endpoint_binding",
    "missing_object_binding",
    "required_field_without_name",
}


def publish_candidates(
    candidates: list[FunctionCandidate],
    publish_threshold: float,
    abstain_threshold: float,
) -> list[FunctionCandidate]:
    for candidate in candidates:
        if _has_critical_error(candidate):
            candidate.status = "rejected"
        elif candidate.confidence >= publish_threshold:
            candidate.status = "published"
        elif candidate.confidence < abstain_threshold:
            candidate.status = "rejected"
        else:
            candidate.status = "abstained"
    return candidates


def _has_critical_error(candidate: FunctionCandidate) -> bool:
    return any(error in CRITICAL_ERRORS or error.startswith("unknown_object:") for error in candidate.validation_errors)
