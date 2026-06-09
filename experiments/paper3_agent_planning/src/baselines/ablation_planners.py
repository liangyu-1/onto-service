"""Ablation planners for controlled experiments."""
from __future__ import annotations

import json
from typing import Any, Dict

from action_bank import ActionBank
from data_loader import RetailDB, Task
from llm_client import LLMClient
from state_manager import DialogueState
from verifier import ConstraintVerifier, VerificationResult

from baselines.schema_baseline import SchemaPlanner
from baselines.ours_planner import OursPlanner


class DuplicateOnlyPlanner(OursPlanner):
    """Schema + duplicate detector only (no precondition/policy checks)."""

    def __init__(self, llm: LLMClient, action_bank: ActionBank):
        # Don't call super().__init__ which creates full verifier
        self.llm = llm
        self.action_bank = action_bank
        self.verifier = DuplicateOnlyVerifier(action_bank)
        self.max_repair = 2


class DuplicateOnlyVerifier(ConstraintVerifier):
    """Verifier that only checks for duplicates and unknown actions."""

    def verify(self, action_name: str, arguments: Dict[str, Any], state: DialogueState, db: Dict[str, Any]) -> VerificationResult:
        schema = self.action_bank.get(action_name)
        if schema is None:
            return VerificationResult(False, [f"Unknown action: {action_name}"])
        if self._check_duplicate(action_name, arguments, state):
            return VerificationResult(False, ["DUPLICATE: Action already executed"])
        return VerificationResult(True, [])


class PreconditionOnlyPlanner(SchemaPlanner):
    """Schema + precondition/policy verifier (no duplicate check, no repair)."""

    def __init__(self, llm: LLMClient, action_bank: ActionBank):
        super().__init__(llm, action_bank)
        self.verifier = PreconditionOnlyVerifier(action_bank)

    def plan_next_action(self, task: Task, state: DialogueState, db: RetailDB):
        action = SchemaPlanner.plan_next_action(self, task, state, db)
        v_result = self.verifier.verify(
            action.get("action", ""),
            action.get("arguments", {}),
            state, db
        )
        # Record violation but don't block execution
        if not v_result.passed:
            action["_violation"] = v_result.violations
        return action


class PreconditionOnlyVerifier(ConstraintVerifier):
    """Verifier that checks preconditions and constraints but not duplicates."""

    def verify(self, action_name: str, arguments: Dict[str, Any], state: DialogueState, db: Dict[str, Any]) -> VerificationResult:
        schema = self.action_bank.get(action_name)
        if schema is None:
            return VerificationResult(False, [f"Unknown action: {action_name}"])

        violations = []
        for precond in schema.preconditions:
            ok, msg = self._check_precondition(precond, arguments, state, db)
            if not ok:
                violations.append(f"PRECONDITION: {msg}")
        for constraint in schema.constraints:
            ok, msg = self._check_constraint(constraint, arguments, state, db)
            if not ok:
                violations.append(f"CONSTRAINT: {msg}")

        return VerificationResult(len(violations) == 0, violations)


class BlockingNoRepairPlanner(SchemaPlanner):
    """Schema + full verifier (blocking) but NO repair loop."""

    def __init__(self, llm: LLMClient, action_bank: ActionBank):
        super().__init__(llm, action_bank)
        self.verifier = ConstraintVerifier(action_bank)

    def plan_next_action(self, task: Task, state: DialogueState, db: RetailDB):
        action = SchemaPlanner.plan_next_action(self, task, state, db)
        v_result = self.verifier.verify(
            action.get("action", ""),
            action.get("arguments", {}),
            state, db
        )
        if not v_result.passed:
            return {
                "thought": f"Action blocked by verifier: {v_result.violations}",
                "action": "transfer_to_human_agents",
                "arguments": {"reason": "verification_failed", "violations": v_result.violations},
                "_blocked": True,
                "_violations": v_result.violations,
            }
        return action
