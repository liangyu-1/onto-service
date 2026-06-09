"""Ontology-grounded action planner with constraint verification."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from action_bank import ActionBank
from llm_client import LLMClient
from state_manager import DialogueState
from verifier import ConstraintVerifier, VerificationResult


SYSTEM_PROMPT = """You are a customer service agent assistant. Your job is to select the next action to take based on the user's request and the current state.

You have access to the following actions:
{action_bank}

Current state:
- User authenticated: {user_authenticated}
- User ID: {user_id}
- Cached orders: {cached_orders}
- Cached products: {cached_products}

Policy reminders:
- You must authenticate the user before taking any action.
- Before updating the database (cancel, modify, return, exchange), you must get explicit user confirmation.
- You can only help one user per conversation.
- You should deny requests that violate policy.

Respond with a JSON object:
{{
  "thought": "your reasoning about what to do next",
  "action": "action_id or 'respond_to_user' or 'ask_for_confirmation'",
  "arguments": {{"param": "value"}},
  "needs_confirmation": true/false
}}
"""


class OntologyPlanner:
    """Planner that uses ActionBank + Verifier + Repair loop."""

    def __init__(self, action_bank: ActionBank, verifier: ConstraintVerifier, llm: LLMClient):
        self.action_bank = action_bank
        self.verifier = verifier
        self.llm = llm
        self.max_repair_attempts = 3

    def plan_next_action(
        self,
        task_description: str,
        state: DialogueState,
        db: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Plan the next action with verification and repair."""
        
        # Build prompt
        action_bank_text = self.action_bank.to_prompt_text()
        cached_orders = list(state.cached_orders.keys())
        cached_products = list(state.cached_products.keys())
        
        system = SYSTEM_PROMPT.format(
            action_bank=action_bank_text,
            user_authenticated=state.user_authenticated,
            user_id=state.user_id,
            cached_orders=cached_orders,
            cached_products=cached_products,
        )

        # Build conversation history
        history_text = "\n".join(
            f"{h.get('role', 'system')}: {h.get('content', str(h))}"
            for h in state.history[-10:]  # Last 10 turns
        )

        user_prompt = f"""Task: {task_description}

Conversation history:
{history_text}

What is the next action to take?"""

        # Try with repair loop
        for attempt in range(self.max_repair_attempts):
            response = self.llm.chat_json(system, user_prompt)
            action_name = response.get("action", "")
            arguments = response.get("arguments", {})
            
            # Special actions that don't need verification
            if action_name in ("respond_to_user", "ask_for_confirmation"):
                return response

            # Verify the action
            result = self.verifier.verify(action_name, arguments, state, db)
            if result.passed:
                return response

            # Repair: add violation feedback to prompt
            violations_text = "\n".join(f"- {v}" for v in result.violations)
            user_prompt += f"""

Your proposed action '{action_name}' was rejected by the constraint verifier:
{violations_text}

Please propose a different action that satisfies all constraints."""

        # Max repairs reached, return last response anyway
        return response
