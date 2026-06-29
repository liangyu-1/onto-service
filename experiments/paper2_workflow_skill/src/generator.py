"""Workflow Skill generation."""

from __future__ import annotations

import json
import re
from typing import Any

from .llm_client import ChatClient
from .schema import DocumentRecord, FunctionSpec, OntologyWorkflowSkill, WorkflowEdge, WorkflowNode


def generate_workflows(
    documents: list[DocumentRecord],
    ontology: dict[str, Any],
    functions: list[FunctionSpec],
    base_url: str | None,
    model: str | None,
    api_key_env: str,
    timeout: float,
) -> list[OntologyWorkflowSkill]:
    client = None
    if base_url or model:
        if not base_url or not model:
            raise ValueError("--llm-base-url and --llm-model must be provided together")
        client = ChatClient(base_url=base_url, model=model, api_key_env=api_key_env, timeout=timeout)
    workflows = []
    for doc in documents:
        if client:
            workflows.append(_generate_with_llm(client, doc, ontology, functions))
        else:
            workflows.append(_generate_heuristic(doc, functions))
    return workflows


def _generate_heuristic(doc: DocumentRecord, functions: list[FunctionSpec]) -> OntologyWorkflowSkill:
    units = _extract_units(doc)
    skill = OntologyWorkflowSkill(
        skill_id=f"skill_{_safe_id(doc.source_id)}",
        source_id=doc.source_id,
        goal_predicate=_infer_goal(doc),
    )
    variable_types: dict[str, str] = {}
    for index, unit in enumerate(units):
        function = _ground_function(unit["text"], functions)
        object_variables = []
        if function:
            for object_type in function.bound_object_types:
                variable_name = f"v_{_safe_id(object_type)}"
                variable_types[variable_name] = object_type
                object_variables.append(variable_name)
        node = WorkflowNode(
            node_id=f"n{index}",
            node_type="OntologyFunctionCall" if function else "UnresolvedCapability",
            text=unit["text"],
            function_id=function.function_id if function else None,
            object_variables=object_variables,
            state_predicates=_state_predicates(unit["text"]),
            evidence={"span": unit.get("span", {}), "source": "document"},
        )
        if not function:
            skill.unresolved_regions.append(unit["text"])
        skill.nodes.append(node)
        if index > 0:
            skill.control_edges.append(WorkflowEdge(source=f"n{index - 1}", target=f"n{index}"))
    skill.object_variables = [
        {"name": variable_name, "type": object_type}
        for variable_name, object_type in sorted(variable_types.items())
    ]
    return skill


def _generate_with_llm(
    client: ChatClient,
    doc: DocumentRecord,
    ontology: dict[str, Any],
    functions: list[FunctionSpec],
) -> OntologyWorkflowSkill:
    prompt = {
        "task": "Generate an OntologyWorkflowSkill from a procedural document.",
        "constraints": [
            "Return strict JSON only.",
            "Function-call nodes must use function_id from the provided Function Layer.",
            "Do not invent functions. Use node_type=Unresolved when no function matches.",
            "Represent conditions as ontology state predicates when possible.",
        ],
        "document": {"source_id": doc.source_id, "domain": doc.domain, "text": doc.text[:12000]},
        "ontology_summary": _ontology_summary(ontology),
        "function_layer": [_function_prompt(function) for function in functions[:200]],
        "output_schema": {
            "skill_id": "string",
            "source_id": "string",
            "goal_predicate": "string|null",
            "nodes": [{"node_id": "string", "node_type": "OntologyFunctionCall|Decision|UserInteraction|End|Unresolved", "text": "string", "function_id": "string|null", "object_variables": ["string"], "state_predicates": ["string"]}],
            "control_edges": [{"source": "string", "target": "string", "edge_type": "sequence|condition|exception|loop", "condition": "string|null"}],
            "dataflow_edges": [{"source": "string", "target": "string", "edge_type": "data", "condition": "string|null"}],
            "invariants": ["string"],
            "exception_paths": [{"source": "string", "target": "string", "edge_type": "exception", "condition": "string|null"}],
            "unresolved_regions": ["string"],
        },
    }
    raw = client.complete_json(
        [
            {"role": "system", "content": "You induce ontology-grounded executable workflow skills."},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ]
    )
    return _workflow_from_dict(raw, fallback_source_id=doc.source_id)


def _extract_units(doc: DocumentRecord) -> list[dict[str, Any]]:
    if doc.actions:
        return [
            {
                "text": str(action.get("span", {}).get("text") or action.get("text") or ""),
                "span": action.get("span", {}),
            }
            for action in doc.actions
            if str(action.get("span", {}).get("text") or action.get("text") or "").strip()
        ]
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", doc.text) if part.strip()]
    return [{"text": part, "span": {}} for part in parts]


def _ground_function(text: str, functions: list[FunctionSpec]) -> FunctionSpec | None:
    text_tokens = set(_tokens(text))
    best = None
    best_score = 0
    for function in functions:
        haystack = " ".join([function.function_id, function.description, *function.bound_object_types])
        score = len(text_tokens & set(_tokens(haystack)))
        if score > best_score:
            best = function
            best_score = score
    return best if best_score > 0 else None


def _state_predicates(text: str) -> list[str]:
    low = text.lower()
    predicates = []
    for marker in ("if ", "when ", "once ", "after ", "before ", "unless "):
        if marker in low:
            predicates.append(f"condition:{text[:120]}")
            break
    if any(word in low for word in ("warning", "caution", "do not", "must", "should")):
        predicates.append(f"invariant:{text[:120]}")
    return predicates


def _infer_goal(doc: DocumentRecord) -> str | None:
    title = doc.metadata.get("title") or doc.metadata.get("subject")
    return f"complete:{title}" if title else None


def _ontology_summary(ontology: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": ontology.get("metadata", {}).get("name"),
        "object_type_count": len(ontology.get("object_types", [])),
        "sample_object_types": ontology.get("object_types", [])[:30],
    }


def _function_prompt(function: FunctionSpec) -> dict[str, Any]:
    return {
        "function_id": function.function_id,
        "description": function.description,
        "bound_object_types": list(function.bound_object_types),
        "inputs": list(function.inputs),
        "outputs": list(function.outputs),
        "preconditions": list(function.preconditions),
        "effects": list(function.effects),
    }


def _workflow_from_dict(raw: dict[str, Any], fallback_source_id: str) -> OntologyWorkflowSkill:
    skill = OntologyWorkflowSkill(
        skill_id=str(raw.get("skill_id") or f"skill_{_safe_id(fallback_source_id)}"),
        source_id=str(raw.get("source_id") or fallback_source_id),
        goal_predicate=raw.get("goal_predicate"),
        typed_inputs=list(raw.get("typed_inputs", [])),
        typed_outputs=list(raw.get("typed_outputs", [])),
        object_variables=list(raw.get("object_variables", [])),
        invariants=list(raw.get("invariants", [])),
        unresolved_regions=list(raw.get("unresolved_regions", [])),
    )
    skill.nodes = [
        WorkflowNode(
            node_id=str(node.get("node_id", "")),
            node_type=str(node.get("node_type", "Unresolved")),
            text=str(node.get("text", "")),
            function_id=node.get("function_id"),
            object_variables=list(node.get("object_variables", [])),
            state_predicates=list(node.get("state_predicates", [])),
            evidence=dict(node.get("evidence", {})),
        )
        for node in raw.get("nodes", [])
    ]
    skill.control_edges = [_edge_from_dict(edge, default_type="sequence") for edge in raw.get("control_edges", [])]
    skill.dataflow_edges = [_edge_from_dict(edge, default_type="data") for edge in raw.get("dataflow_edges", [])]
    skill.exception_paths = [_edge_from_dict(edge, default_type="exception") for edge in raw.get("exception_paths", [])]
    return skill


def _edge_from_dict(edge: dict[str, Any], default_type: str) -> WorkflowEdge:
    return WorkflowEdge(
        source=str(edge.get("source", "")),
        target=str(edge.get("target", "")),
        edge_type=str(edge.get("edge_type", default_type)),
        condition=edge.get("condition"),
    )


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _safe_id(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower() or "unknown"
