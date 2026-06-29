"""Evidence-bearing contract generation for ontology functions.

The deterministic discovery and alignment stages are useful baselines. The full
method can additionally call an OpenAI-compatible LLM endpoint to infer fields
that require semantic synthesis, such as preconditions, effects, and error
contracts. The generator never fabricates evidence: it can only propose fields
from the candidate's local artifact text and ontology neighborhood.
"""

from __future__ import annotations

import json
from typing import Any

from .llm_client import ChatClient
from .schema import Evidence, FunctionCandidate, ObjectLayer


def generate_contracts(
    candidates: list[FunctionCandidate],
    ontology: ObjectLayer,
    base_url: str | None,
    model: str | None,
    api_key_env: str,
    timeout: float,
) -> list[FunctionCandidate]:
    if not base_url and not model:
        return candidates
    if not base_url or not model:
        raise ValueError("--llm-base-url and --llm-model must be provided together")

    client = ChatClient(base_url=base_url, model=model, api_key_env=api_key_env, timeout=timeout)
    for candidate in candidates:
        patch = _request_contract_patch(client, candidate, ontology)
        _apply_patch(candidate, patch)
    return candidates


def _request_contract_patch(
    client: ChatClient,
    candidate: FunctionCandidate,
    ontology: ObjectLayer,
) -> dict[str, Any]:
    prompt = {
        "task": "Infer missing ontology function contract fields from evidence only.",
        "constraints": [
            "Return strict JSON only.",
            "Do not invent endpoint bindings or ontology object names.",
            "Use null or empty lists when evidence is insufficient.",
            "Preconditions and effects must be ontology-state predicates or concise unresolved markers.",
        ],
        "candidate": candidate.to_dict(),
        "ontology_neighborhood": _ontology_neighborhood(candidate, ontology),
        "output_schema": {
            "preconditions": ["string"],
            "effects": ["string"],
            "error_contract": ["string"],
            "evidence_claims": ["string"],
        },
    }
    content = client.complete_json(
        [
            {
                "role": "system",
                "content": "You construct ontology-bound API function contracts from provided evidence.",
            },
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ]
    )
    if not isinstance(content, dict):
        raise ValueError("LLM contract generator did not return a JSON object")
    return content


def _ontology_neighborhood(candidate: FunctionCandidate, ontology: ObjectLayer) -> dict[str, Any]:
    objects = []
    for obj in ontology.object_types:
        if candidate.bound_object_types and obj.id not in candidate.bound_object_types:
            continue
        objects.append(
            {
                "id": obj.id,
                "aliases": list(obj.aliases),
                "properties": [
                    {"id": prop.id, "type": prop.type, "aliases": list(prop.aliases)}
                    for prop in obj.properties
                ],
                "states": list(obj.states),
            }
        )
    return {"object_types": objects}


def _apply_patch(candidate: FunctionCandidate, patch: dict[str, Any]) -> None:
    for field in ("preconditions", "effects", "error_contract"):
        values = patch.get(field)
        if isinstance(values, list):
            existing = getattr(candidate, field)
            for value in values:
                if isinstance(value, str) and value and value not in existing:
                    existing.append(value)
    claims = patch.get("evidence_claims")
    if isinstance(claims, list):
        for claim in claims:
            if isinstance(claim, str) and claim:
                candidate.evidence_set.append(
                    Evidence(
                        source_type="llm_contract_generator",
                        source_id=candidate.function_id,
                        claim=claim,
                        confidence=0.5,
                    )
                )
