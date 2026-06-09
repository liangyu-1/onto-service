"""Evaluation metrics for agent planning."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class EvaluationResult:
    task_id: str
    success: bool = False
    action_accuracy: float = 0.0  # % of actions matching gold
    policy_violations: int = 0
    invalid_actions: int = 0
    constraint_violations: int = 0
    repair_attempts: int = 0
    repair_successes: int = 0
    predicted_actions: List[Dict[str, Any]] = field(default_factory=list)
    gold_actions: List[Dict[str, Any]] = field(default_factory=list)
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "success": self.success,
            "action_accuracy": round(self.action_accuracy, 4),
            "policy_violations": self.policy_violations,
            "invalid_actions": self.invalid_actions,
            "constraint_violations": self.constraint_violations,
            "repair_attempts": self.repair_attempts,
            "repair_successes": self.repair_successes,
            "predicted_count": len(self.predicted_actions),
            "gold_count": len(self.gold_actions),
            "error_message": self.error_message,
        }


def compute_action_accuracy(predicted: List[Dict[str, Any]], gold: List[Dict[str, Any]]) -> float:
    """Compute accuracy as % of predicted actions that match gold (by name and args)."""
    if not gold:
        return 1.0 if not predicted else 0.0
    if not predicted:
        return 0.0

    matches = 0
    for i, gold_action in enumerate(gold):
        if i >= len(predicted):
            break
        pred = predicted[i]
        if actions_match(pred, gold_action):
            matches += 1

    return matches / len(gold)


def actions_match(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    """Check if two actions match (same name, same arguments)."""
    if a.get("action") != b.get("name") and a.get("action") != b.get("action"):
        return False
    a_args = a.get("arguments", {})
    b_args = b.get("arguments", {})
    # Simple comparison - could be more sophisticated
    return a_args == b_args


def aggregate_results(results: List[EvaluationResult]) -> Dict[str, Any]:
    """Aggregate results across tasks."""
    if not results:
        return {}

    n = len(results)
    successes = sum(1 for r in results if r.success)
    total_policy_violations = sum(r.policy_violations for r in results)
    total_invalid = sum(r.invalid_actions for r in results)
    total_constraint_violations = sum(r.constraint_violations for r in results)
    total_repairs = sum(r.repair_attempts for r in results)
    total_repair_success = sum(r.repair_successes for r in results)

    return {
        "tasks_evaluated": n,
        "task_success_rate": round(successes / n, 4),
        "avg_action_accuracy": round(sum(r.action_accuracy for r in results) / n, 4),
        "total_policy_violations": total_policy_violations,
        "policy_violation_rate": round(total_policy_violations / n, 4),
        "total_invalid_actions": total_invalid,
        "invalid_action_rate": round(total_invalid / n, 4),
        "total_constraint_violations": total_constraint_violations,
        "constraint_violation_rate": round(total_constraint_violations / n, 4),
        "total_repair_attempts": total_repairs,
        "repair_success_rate": round(total_repair_success / max(total_repairs, 1), 4),
    }
