"""Metrics for Paper 2 workflow-skill experiments."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .schema import DocumentRecord, OntologyWorkflowSkill


def compute_metrics(
    workflows: list[OntologyWorkflowSkill],
    documents: list[DocumentRecord],
    validation_report: dict[str, Any],
    gold_workflows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    gold_action_count = sum(len(doc.actions) for doc in documents)
    predicted_node_count = sum(len(workflow.nodes) for workflow in workflows)
    grounded_nodes = sum(
        1
        for workflow in workflows
        for node in workflow.nodes
        if node.node_type == "OntologyFunctionCall" and node.function_id
    )
    unresolved_nodes = sum(
        1
        for workflow in workflows
        for node in workflow.nodes
        if node.node_type in {"Unresolved", "UnresolvedCapability"}
    )
    violation_count = sum(validation_report.get("error_counts", {}).values())
    metrics = {
        "document_count": len(documents),
        "workflow_count": len(workflows),
        "gold_action_count": gold_action_count,
        "predicted_node_count": predicted_node_count,
        "node_count_ratio_to_gold": predicted_node_count / gold_action_count if gold_action_count else None,
        "function_grounding_rate": grounded_nodes / predicted_node_count if predicted_node_count else 0.0,
        "unresolved_node_rate": unresolved_nodes / predicted_node_count if predicted_node_count else 0.0,
        "ontology_violation_count": violation_count,
        "workflow_valid_rate": _workflow_valid_rate(validation_report),
        "metric_limitations": [
            "Existing public processed datasets only provide partial gold labels.",
            "Function grounding, typed dataflow, state predicates, and executable workflow metrics require a curated Full Ontology Workflow benchmark.",
        ],
    }
    if gold_workflows is not None:
        metrics.update(_gold_workflow_metrics(workflows, gold_workflows))
    return metrics


def _workflow_valid_rate(validation_report: dict[str, Any]) -> float:
    reports = validation_report.get("workflow_reports", [])
    if not reports:
        return 0.0
    valid = sum(1 for report in reports if not report.get("errors"))
    return valid / len(reports)


def _gold_workflow_metrics(
    workflows: list[OntologyWorkflowSkill],
    gold_workflows: list[dict[str, Any]],
) -> dict[str, Any]:
    gold_by_source = {str(row.get("source_id")): row for row in gold_workflows}
    compared = 0
    sequence_exact = 0
    micro_overlap = 0
    micro_pred = 0
    micro_gold = 0
    for workflow in workflows:
        gold = gold_by_source.get(workflow.source_id)
        if not gold:
            continue
        compared += 1
        pred_functions = _predicted_function_sequence(workflow)
        gold_functions = _gold_function_sequence(gold)
        if pred_functions == gold_functions:
            sequence_exact += 1
        pred_counter = Counter(pred_functions)
        gold_counter = Counter(gold_functions)
        micro_overlap += sum((pred_counter & gold_counter).values())
        micro_pred += sum(pred_counter.values())
        micro_gold += sum(gold_counter.values())
    precision = micro_overlap / micro_pred if micro_pred else 0.0
    recall = micro_overlap / micro_gold if micro_gold else 0.0
    return {
        "gold_workflow_count": len(gold_workflows),
        "gold_compared_workflow_count": compared,
        "function_sequence_exact_rate": sequence_exact / compared if compared else 0.0,
        "function_id_multiset_precision": precision,
        "function_id_multiset_recall": recall,
        "function_id_multiset_f1": _f1(precision, recall),
        "gold_metric_limitations": [
            "These metrics compare function IDs only.",
            "Control-flow, data-flow, state-predicate, invariant, and exception metrics require dedicated graph alignment.",
        ],
    }


def _predicted_function_sequence(workflow: OntologyWorkflowSkill) -> list[str]:
    return [
        str(node.function_id)
        for node in workflow.nodes
        if node.node_type == "OntologyFunctionCall" and node.function_id
    ]


def _gold_function_sequence(workflow: dict[str, Any]) -> list[str]:
    return [
        str(node.get("function_id"))
        for node in workflow.get("nodes", [])
        if node.get("node_type") == "OntologyFunctionCall" and node.get("function_id")
    ]


def _f1(precision: float, recall: float) -> float:
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0
