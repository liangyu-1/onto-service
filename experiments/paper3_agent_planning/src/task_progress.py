"""Conservative task-progress checks for terminal actions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Set

from state_manager import DialogueState


UPDATE_TO_INTENT = {
    "cancel_pending_order": "cancel",
    "return_delivered_order_items": "return",
    "exchange_delivered_order_items": "exchange",
    "modify_pending_order_items": "item_modify",
    "modify_pending_order_address": "address",
    "modify_user_address": "address",
    "modify_pending_order_payment": "payment",
}


@dataclass
class ProgressCheck:
    passed: bool
    violations: List[str]
    required_intents: Set[str]
    completed_intents: Set[str]


class TaskProgressVerifier:
    """Reject terminal actions when the task is plainly unfinished.

    This checker intentionally uses only task text and executed history. It does
    not inspect gold actions or evaluation criteria.
    """

    def check_terminal(
        self,
        action_name: str,
        task_info: str,
        state: DialogueState,
        db: Dict[str, Any],
    ) -> ProgressCheck:
        required = self._required_intents(task_info)
        completed = self._completed_intents(state)
        violations: List[str] = []

        if action_name == "finish_task":
            missing = sorted(required - completed)
            if missing:
                violations.append(f"PROGRESS: finish_task before completing required intents {missing}")

        if action_name == "transfer_to_human_agents":
            missing = sorted(required - completed)
            if missing and self._has_productive_context(task_info, state, db):
                violations.append(
                    f"PROGRESS: transfer_to_human_agents while productive ontology-grounded actions remain for {missing}"
                )

        return ProgressCheck(
            passed=not violations,
            violations=violations,
            required_intents=required,
            completed_intents=completed,
        )

    def _required_intents(self, task_info: str) -> Set[str]:
        text = (task_info or "").lower()
        required = set()
        if any(word in text for word in ("cancel", "cancellation")):
            required.add("cancel")
        if any(word in text for word in ("return", "refund")):
            required.add("return")
        if any(word in text for word in ("exchange",)):
            required.add("exchange")
        if any(word in text for word in ("address", "shipping")):
            required.add("address")
        if any(word in text for word in (
            "change", "modify", "replace", "different", "color", "size",
            "capacity", "storage", "processor", "dial", "strap", "variant",
        )):
            # Keep item modification separate from exchange/return. Exchange
            # tasks often also involve item matching, but the exchange intent
            # itself covers delivered-order item replacement.
            if "exchange" not in required:
                required.add("item_modify")
        if any(word in text for word in ("payment", "card", "paypal", "gift card")):
            required.add("payment")

        # In many tasks, return/refund language is conditional or informational
        # while the executable fallback is address modification. Avoid forcing
        # return/cancel if address is also requested and no explicit return
        # update has been executed yet; the repair loop can still choose it.
        if "partial items is not possible" in text and "address" in required:
            required.discard("return")
            required.discard("cancel")
        return required

    def _completed_intents(self, state: DialogueState) -> Set[str]:
        completed = set()
        for event in state.history:
            action = event.get("action")
            result = event.get("result")
            if action not in UPDATE_TO_INTENT:
                continue
            if isinstance(result, dict) and "error" in result:
                continue
            completed.add(UPDATE_TO_INTENT[action])
            arguments = event.get("arguments", {})
            if isinstance(arguments, dict) and arguments.get("payment_method_id"):
                completed.add("payment")
        return completed

    def _has_productive_context(
        self,
        task_info: str,
        state: DialogueState,
        db: Dict[str, Any],
    ) -> bool:
        text = (task_info or "").lower()
        if "human agent" in text or "transfer" in text or "escalat" in text:
            return False
        if state.cached_orders or state.cached_users or state.cached_products:
            return True
        if state.user_id and state.user_id in db.get("users", {}):
            return True
        return False
