"""ReAct baseline: Reasoning + Acting with tool use."""
from __future__ import annotations

import json
from typing import Any, Dict

from src.state_manager import DialogueState
from src.llm_client import LLMClient
from src.action_bank import ActionBank


class ReActPlanner:
    """ReAct-style planner with reasoning traces but no structured ActionBank."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def _extract_task_info(self, task: Any) -> str:
        """Extract task description from tau-bench task."""
        if isinstance(task, dict):
            task_description = task.get("instruction", "")
            user_scenario = task.get("user_scenario", {})
        else:
            task_description = getattr(task, 'instruction', '')
            user_scenario = getattr(task, 'user_scenario', {})
        
        if not task_description and isinstance(user_scenario, dict):
            task_description = user_scenario.get("instruction", "")
            if not task_description and "instructions" in user_scenario:
                ins = user_scenario["instructions"]
                if isinstance(ins, dict):
                    task_description = ins.get("reason_for_call", "")
        
        known_facts = []
        if isinstance(user_scenario, dict):
            known_info = user_scenario.get("instructions", {}).get("known_info", "")
            if known_info:
                known_facts.append(f"Known facts: {known_info}")
        
        parts = [f"Task: {task_description}"]
        if known_facts:
            parts.extend(known_facts)
        return "\n".join(parts)

    def plan_next_action(self, task: Any, state: DialogueState, db: Dict[str, Any]) -> Dict[str, Any]:
        task_info = self._extract_task_info(task)

        # Build history
        history_lines = []
        for h in state.history:
            if "action" in h:
                result = h.get("result", "")
                if isinstance(result, dict) and "error" in result:
                    history_lines.append(f"Action: {h['action']} -> Error: {result['error']}")
                else:
                    history_lines.append(f"Action: {h['action']} -> OK")
        history_text = "\n".join(history_lines[-10:]) if history_lines else "No actions yet."

        system_prompt = """You are a customer service agent. Use the ReAct framework:
1. THINK: Reason about what to do next
2. ACT: Take an action from the available tools

Available tools:
- find_user_id_by_name_zip(first_name, last_name, zip)
- find_user_id_by_email(email)
- get_user_details(user_id)
- get_order_details(user_id, order_id)
- get_product_details(product_id)
- cancel_pending_order(order_id, reason)
- exchange_delivered_order_items(order_id, item_ids, new_item_ids, payment_method_id)
- return_delivered_order_items(order_id, item_ids, payment_method_id)
- modify_pending_order_address(order_id, address)
- modify_pending_order_items(order_id, item_ids, new_item_ids, payment_method_id)
- modify_user_address(user_id, address)
- transfer_to_human_agents(summary)

Rules:
- Authenticate the user first
- Gather information before taking action
- Use exact values from the task description

Respond with JSON:
{
  "thought": "your reasoning",
  "action": "tool_name",
  "arguments": {"param": "value"}
}"""

        user_prompt = f"""{task_info}

History:
{history_text}

Current state:
- Authenticated: {state.user_authenticated}
- User ID: {state.user_id}
- Orders: {list(state.cached_orders.keys())}

Think step by step. What is the next action?"""

        try:
            response = self.llm.chat_json(system_prompt, user_prompt)
            return {
                "thought": response.get("thought", ""),
                "action": response.get("action", ""),
                "arguments": response.get("arguments", {}),
            }
        except Exception as e:
            return {
                "thought": f"Error: {e}",
                "action": "transfer_to_human_agents",
                "arguments": {"summary": "Planning failed."},
            }
