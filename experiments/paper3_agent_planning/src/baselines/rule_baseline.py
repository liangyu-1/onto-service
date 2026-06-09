"""Rule-based baseline that follows gold actions (for pipeline validation)."""
from __future__ import annotations

from typing import Any, Dict, List

from state_manager import DialogueState


class RuleBaselinePlanner:
    """A rule-based planner that simply follows the gold action sequence.
    This is NOT a real baseline - it's for pipeline validation only."""

    def __init__(self, gold_actions: List[Dict[str, Any]]):
        self.gold_actions = gold_actions
        self.step = 0

    def plan_next_action(self, task_description: str, state: DialogueState, db: Dict[str, Any]) -> Dict[str, Any]:
        if self.step >= len(self.gold_actions):
            return {"action": "respond_to_user", "arguments": {}, "thought": "Done"}

        gold = self.gold_actions[self.step]
        self.step += 1
        return {
            "action": gold["name"],
            "arguments": gold.get("arguments", {}),
            "thought": f"Following gold action {self.step}",
        }
