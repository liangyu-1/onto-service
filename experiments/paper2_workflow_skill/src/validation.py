"""Validation for ontology Workflow Skills."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .schema import FunctionSpec, OntologyWorkflowSkill


def validate_workflows(
    workflows: list[OntologyWorkflowSkill],
    ontology: dict[str, Any],
    functions: list[FunctionSpec],
) -> dict[str, Any]:
    function_ids = {function.function_id for function in functions}
    object_ids = _object_ids(ontology)
    errors: Counter[str] = Counter()
    workflow_reports = []

    for workflow in workflows:
        node_ids = {node.node_id for node in workflow.nodes}
        variable_types = {
            str(variable.get("name")): str(variable.get("type"))
            for variable in workflow.object_variables
            if variable.get("name") and variable.get("type")
        }
        wf_errors = []
        for node in workflow.nodes:
            if node.node_type == "OntologyFunctionCall" and not node.function_id:
                wf_errors.append("function_node_without_function_id")
            if node.function_id and node.function_id not in function_ids:
                wf_errors.append(f"unknown_function:{node.function_id}")
            for variable_name in node.object_variables:
                variable_type = variable_types.get(str(variable_name))
                if not variable_type:
                    wf_errors.append(f"unknown_variable:{variable_name}")
                elif object_ids and variable_type not in object_ids:
                    wf_errors.append(f"unknown_object_type:{variable_type}")
        for edge in [*workflow.control_edges, *workflow.dataflow_edges, *workflow.exception_paths]:
            if _edge_node_id(edge.source) not in node_ids or _edge_node_id(edge.target) not in node_ids:
                wf_errors.append("edge_references_unknown_node")
        if not workflow.nodes:
            wf_errors.append("empty_workflow")
        errors.update(wf_errors)
        workflow_reports.append({"skill_id": workflow.skill_id, "errors": wf_errors})

    return {
        "workflow_count": len(workflows),
        "error_counts": dict(errors),
        "workflow_reports": workflow_reports,
    }


def _object_ids(ontology: dict[str, Any]) -> set[str]:
    ids = set()
    for obj in ontology.get("object_types", []):
        obj_id = obj.get("id")
        if obj_id:
            ids.add(str(obj_id))
    return ids


def _edge_node_id(endpoint: str) -> str:
    return endpoint.split(".", 1)[0]
