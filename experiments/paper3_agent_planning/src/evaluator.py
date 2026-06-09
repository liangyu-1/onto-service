"""Tau-bench-style local evaluation helpers.

This module is intentionally conservative. It does not claim to reproduce the
official tau-bench dialogue/user simulator. It evaluates executable action
traces against the local retail simulator and records which parts of the
tau-bench reward are covered locally.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import importlib.util
import json
from typing import Any, Dict, List, Optional, Tuple

from simulator import RetailSimulator
from state_manager import DialogueState


UPDATE_ACTIONS = {
    "modify_user_address",
    "modify_pending_order_address",
    "modify_pending_order_items",
    "modify_pending_order_payment",
    "cancel_pending_order",
    "return_delivered_order_items",
    "exchange_delivered_order_items",
}

TERMINAL_ACTIONS = {"finish_task", "transfer_to_human_agents"}


@dataclass
class LocalRewardResult:
    """Local reward approximation for a tau-bench task."""

    final_name_match: bool
    final_exact_match: bool
    db_state_match: bool
    db_hash_match: bool
    local_success: bool
    strict_success: bool
    reward_basis: List[str]
    local_db_reward: bool
    local_communicate_reward: Optional[bool]
    local_nl_assertion_reward: Optional[bool]
    nl_assertions_supported: bool
    communicate_info_supported: bool
    expected_final_action: Optional[Dict[str, Any]]
    predicted_final_action: Optional[Dict[str, Any]]
    expected_db_hash: str
    predicted_db_hash: str
    db_mismatch_summary: Dict[str, Any]
    expected_db_projection: Dict[str, Any]
    predicted_db_projection: Dict[str, Any]
    expected_replay_errors: List[str]
    predicted_execution_errors: List[str]
    evaluator_name: str
    evaluator_scope: str
    official_tau_bench_available: bool
    coverage_warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LocalTauBenchEvaluator:
    """Evaluate traces with local DB-state replay.

    The evaluator replays the gold action sequence with automatic confirmation
    before update actions. It then compares the predicted full DB end state to
    the replayed gold DB end state. This matches the official tau-bench DB
    component more closely than checking a final tool call or only projected
    objects, although it still does not replace the official dialogue/user
    simulator and communication/NL assertion evaluators.
    """

    def __init__(self, db_dict: Dict[str, Any]):
        self.db_dict = db_dict
        self.official_tau_bench_available = self._official_tau_bench_available()

    def evaluate(
        self,
        task: Any,
        predicted_calls: List[Dict[str, Any]],
        executed_violation_count: int,
        invalid_count: int,
        predicted_execution_errors: List[str],
    ) -> LocalRewardResult:
        gold_calls = [
            {"action": ga["name"], "arguments": ga.get("arguments", {})}
            for ga in task.gold_actions
        ]
        expected_final = self._last_effective_action(gold_calls)
        predicted_final = self._last_effective_action(predicted_calls)

        expected_sim, expected_errors = self._replay(gold_calls, auto_confirm=True)
        expected_full_db = expected_sim.db
        expected_db_hash = self._db_hash(expected_full_db)
        expected_projection = self._project_db(expected_sim.db, gold_calls)

        # The caller already executed the predicted trace, but does not expose
        # the simulator object. Replaying here gives a stable DB snapshot using
        # exactly the serialized predicted calls.
        predicted_sim, replay_errors = self._replay(predicted_calls, auto_confirm=False)
        predicted_full_db = predicted_sim.db
        predicted_db_hash = self._db_hash(predicted_full_db)
        predicted_projection = self._project_db(predicted_sim.db, gold_calls, predicted_calls)
        all_predicted_errors = list(predicted_execution_errors) + replay_errors

        final_name_match = bool(
            expected_final
            and predicted_final
            and predicted_final.get("action") == expected_final.get("action")
        )
        final_exact_match = self._actions_match(predicted_final, expected_final)
        db_hash_match = expected_db_hash == predicted_db_hash
        db_state_match = db_hash_match

        ec = getattr(task, "evaluation_criteria", {}) or {}
        reward_basis = list(ec.get("reward_basis") or [])
        nl_assertions = ec.get("nl_assertions")
        communicate_info = ec.get("communicate_info")
        nl_supported = not bool(nl_assertions)
        communicate_supported = not bool(communicate_info)
        local_db_reward = db_hash_match
        local_communicate_reward = True if communicate_supported else None
        local_nl_assertion_reward = True if nl_supported else None

        local_success = db_state_match
        strict_success = (
            local_success
            and executed_violation_count == 0
            and invalid_count == 0
            and not all_predicted_errors
            and nl_supported
            and communicate_supported
        )

        coverage_warnings = []
        if expected_errors:
            coverage_warnings.append(
                "Gold trace has local replay errors; DB projection reward remains usable, "
                "but this local evaluator does not fully reproduce tau-bench user/tool semantics."
            )
        if not nl_supported:
            coverage_warnings.append("NL assertion criteria are present but not evaluated by the local DB evaluator.")
        if not communicate_supported:
            coverage_warnings.append("Communicate-info criteria are present but not evaluated by the local DB evaluator.")
        non_db_reward_types = [
            r for r in reward_basis
            if r not in {"DB"} and not (r == "NL_ASSERTION" and nl_supported)
        ]
        if non_db_reward_types:
            coverage_warnings.append(
                f"Reward basis contains locally unsupported components: {sorted(set(non_db_reward_types))}."
            )

        return LocalRewardResult(
            final_name_match=final_name_match,
            final_exact_match=final_exact_match,
            db_state_match=db_state_match,
            db_hash_match=db_hash_match,
            local_success=local_success,
            strict_success=strict_success,
            reward_basis=reward_basis,
            local_db_reward=local_db_reward,
            local_communicate_reward=local_communicate_reward,
            local_nl_assertion_reward=local_nl_assertion_reward,
            nl_assertions_supported=nl_supported,
            communicate_info_supported=communicate_supported,
            expected_final_action=expected_final,
            predicted_final_action=predicted_final,
            expected_db_hash=expected_db_hash,
            predicted_db_hash=predicted_db_hash,
            db_mismatch_summary=self._db_mismatch_summary(expected_full_db, predicted_full_db),
            expected_db_projection=expected_projection,
            predicted_db_projection=predicted_projection,
            expected_replay_errors=expected_errors,
            predicted_execution_errors=all_predicted_errors,
            evaluator_name="local_tau_bench_db_hash",
            evaluator_scope="Full DB hash after replaying tau-bench retail actions; not official tau-bench reward",
            official_tau_bench_available=self.official_tau_bench_available,
            coverage_warnings=coverage_warnings,
        )

    def _official_tau_bench_available(self) -> bool:
        return any(
            importlib.util.find_spec(module_name) is not None
            for module_name in ("tau_bench", "taubench")
        )

    def _db_hash(self, db: Dict[str, Any]) -> str:
        payload = json.dumps(db, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _db_mismatch_summary(self, expected: Dict[str, Any], predicted: Dict[str, Any]) -> Dict[str, Any]:
        summary: Dict[str, Any] = {}
        for root_key in sorted(set(expected) | set(predicted)):
            expected_bucket = expected.get(root_key, {})
            predicted_bucket = predicted.get(root_key, {})
            if expected_bucket == predicted_bucket:
                continue
            if isinstance(expected_bucket, dict) and isinstance(predicted_bucket, dict):
                changed_ids = [
                    str(item_id)
                    for item_id in sorted(set(expected_bucket) | set(predicted_bucket), key=str)
                    if expected_bucket.get(item_id) != predicted_bucket.get(item_id)
                ]
                summary[root_key] = {
                    "mismatch_count": len(changed_ids),
                    "sample_ids": changed_ids[:10],
                }
            else:
                summary[root_key] = {"mismatch": True}
        return summary

    def _replay(
        self,
        action_calls: List[Dict[str, Any]],
        auto_confirm: bool,
    ) -> Tuple[RetailSimulator, List[str]]:
        sim = RetailSimulator(self.db_dict)
        state = DialogueState()
        errors: List[str] = []

        for call in action_calls:
            action = call.get("action", "")
            args = call.get("arguments", {})
            if auto_confirm and action in UPDATE_ACTIONS:
                state.user_confirmed = True
            try:
                result = sim.execute(action, args, state)
                if action in ("find_user_id_by_email", "find_user_id_by_name_zip"):
                    state.user_id = result
                    state.user_authenticated = True
                if action in UPDATE_ACTIONS:
                    state.user_confirmed = False
                state.history.append({"action": action, "arguments": args, "result": result})
            except Exception as exc:
                errors.append(f"{action}: {exc}")
                state.history.append({"action": action, "arguments": args, "result": {"error": str(exc)}})

        return sim, errors

    def _project_db(
        self,
        db: Dict[str, Any],
        expected_calls: List[Dict[str, Any]],
        predicted_calls: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        if not expected_calls:
            return {}

        expected_transfer = any(c.get("action") == "transfer_to_human_agents" for c in expected_calls)
        if expected_transfer:
            if predicted_calls is None:
                return {"transfer_to_human_agents": True}
            predicted_transfer = bool(
                any(c.get("action") == "transfer_to_human_agents" for c in predicted_calls)
            )
            return {"transfer_to_human_agents": predicted_transfer}

        order_ids = []
        user_ids = []
        for call in expected_calls:
            action = call.get("action")
            args = call.get("arguments", {})
            if action in UPDATE_ACTIONS - {"modify_user_address"}:
                order_id = args.get("order_id")
                if order_id and order_id not in order_ids:
                    order_ids.append(order_id)
            elif action == "modify_user_address":
                user_id = args.get("user_id")
                if user_id and user_id not in user_ids:
                    user_ids.append(user_id)

        projection: Dict[str, Any] = {}
        if order_ids:
            projection["orders"] = {order_id: db.get("orders", {}).get(order_id) for order_id in order_ids}
        if user_ids:
            projection["users"] = {user_id: db.get("users", {}).get(user_id) for user_id in user_ids}
        return projection

    def _last_effective_action(self, calls: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        for call in reversed(calls):
            if call.get("action") != "finish_task":
                return call
        return calls[-1] if calls else None

    def _actions_match(
        self,
        predicted: Optional[Dict[str, Any]],
        gold: Optional[Dict[str, Any]],
    ) -> bool:
        if not predicted or not gold:
            return False
        return (
            predicted.get("action") == gold.get("action")
            and predicted.get("arguments", {}) == gold.get("arguments", {})
        )
