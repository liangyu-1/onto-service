"""Schema baseline: Give LLM the full ActionBank but no verifier."""
from __future__ import annotations

import json
from typing import Any, Dict

from src.state_manager import DialogueState
from src.llm_client import LLMClient
from src.action_bank import ActionBank


# Few-shot example from train set (task 0)
FEW_SHOT_EXAMPLE = """EXAMPLE TASK:
You received your order #W2378156 and wish to exchange the mechanical keyboard for the same one but with clicky switches and the smart thermostat for one compatible with Google Home instead of Apple HomeKit. If there is no keyboard that is clicky, RGB backlight, full size, you'd go for no backlight.
Known: You are Yusuf Rossi in zip code 19122.

EXAMPLE EXECUTION:
Step 1: find_user_id_by_name_zip(first_name="Yusuf", last_name="Rossi", zip="19122") -> OK, user_id=yusuf_rossi_9620
Step 2: get_order_details(order_id="#W2378156") -> OK, items=["Headphones(product=6992792933)", "Vacuum Cleaner(product=1762337868)", "Mechanical Keyboard(product=1656367028, item_id=1151293680)", "Smart Thermostat(product=4896585277, item_id=4983901480)", "Smart Watch(product=6945232052)"]
Step 3: get_product_details(product_id="1656367028") -> OK, variants=[clicky+RGB+full size(unavailable), clicky+none+full size(available=7706410293), ...]
Step 4: get_product_details(product_id="4896585277") -> OK, variants=[Google HomeKit+black(available=7747408585), ...]
Step 5: exchange_delivered_order_items(order_id="#W2378156", item_ids=["1151293680", "4983901480"], new_item_ids=["7706410293", "7747408585"], payment_method_id="credit_card_9513926")
"""


class SchemaPlanner:
    """Planner that uses ActionBank schema in prompt but no runtime verifier."""

    def __init__(self, llm: LLMClient, action_bank: ActionBank):
        self.llm = llm
        self.action_bank = action_bank

    def _call_llm_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Call LLM with JSON-mode; retry once on parse failure."""
        for json_attempt in range(2):
            try:
                return self.llm.chat_json(system_prompt, user_prompt)
            except Exception:
                if json_attempt == 0:
                    user_prompt += (
                        "\n\nREMINDER: Return ONLY a single valid JSON object. "
                        "Do not include any explanatory text before or after the JSON."
                    )
                    continue
                raise

    def _extract_task_info(self, task: Any) -> str:
        """Extract task description and known facts from tau-bench task."""
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
        
        # Extract known facts for better prompting
        known_facts = []
        if isinstance(user_scenario, dict):
            known_info = user_scenario.get("instructions", {}).get("known_info", "")
            if known_info:
                known_facts.append(f"Known facts: {known_info}")
        
        parts = [f"Task: {task_description}"]
        if known_facts:
            parts.extend(known_facts)
        return "\n".join(parts)

    def _format_result(self, action: str, result: Dict) -> str:
        """Format action result into a concise summary for the LLM."""
        if isinstance(result, dict) and "error" in result:
            return f"ERROR: {result['error']}"
        
        if action == 'find_user_id_by_name_zip' or action == 'find_user_id_by_email':
            if isinstance(result, str):
                return f"OK, user_id={result}"
            return f"OK, user_id={result.get('user_id', 'unknown')}"
        
        if action == 'get_user_details':
            orders = result.get('orders', [])
            payment_methods = list(result.get('payment_methods', {}).keys())
            return f"OK, orders={orders}, payment_methods={payment_methods}"
        
        if action == 'get_order_details':
            items = result.get('items', [])
            item_summaries = []
            for item in items:
                name = item.get('name', '')
                pid = item.get('product_id', '')
                iid = item.get('item_id', '')
                price = item.get('price', '')
                opts = item.get('options', {})
                item_summaries.append(f"{name}(product={pid},item={iid},price={price},options={opts})")
            status = result.get('status', 'unknown')
            payment = result.get('payment_history', [{}])[0].get('payment_method_id', '')
            return f"OK, status={status}, payment={payment}, items={item_summaries}"
        
        if action == 'get_product_details':
            name = result.get('name', '')
            variants = result.get('variants', {})
            variant_summaries = []
            for vid, v in variants.items():
                opts = v.get('options', {})
                avail = v.get('available', False)
                price = v.get('price', '')
                if avail:
                    variant_summaries.append(f"{opts}(item_id={vid},price={price})")
            return f"OK, name={name}, available_variants={variant_summaries[:5]}"

        if action == 'get_item_details':
            if isinstance(result, dict):
                return (
                    f"OK, item_id={result.get('item_id', '')}, "
                    f"price={result.get('price', '')}, options={result.get('options', {})}, "
                    f"available={result.get('available', '')}"
                )
            return f"OK, item={result}"
        
        if action == 'cancel_pending_order':
            return "OK, order cancelled"
        
        if action == 'exchange_delivered_order_items':
            return "OK, items exchanged"
        
        if action == 'return_delivered_order_items':
            return "OK, items returned"
        
        return "OK"

    def plan_next_action(self, task: Any, state: DialogueState, db: Dict[str, Any]) -> Dict[str, Any]:
        task_info = self._extract_task_info(task)
        action_bank_text = self.action_bank.to_prompt_text()

        # Build execution history with results
        history_lines = []
        for h in state.history:
            if "action" in h:
                result_summary = self._format_result(h['action'], h.get('result', {}))
                history_lines.append(f"- {h['action']}({json.dumps(h.get('arguments', {}))}) -> {result_summary}")
        
        history_text = "\n".join(history_lines[-10:]) if history_lines else "No actions taken yet."

        system_prompt = f"""You are a customer service agent for a retail store. Solve the customer's request step by step.

{FEW_SHOT_EXAMPLE}

Available actions:
{action_bank_text}

CRITICAL RULES:
1. You MUST authenticate the user FIRST using find_user_id_by_name_zip or find_user_id_by_email.
2. Use the EXACT values from the task description (names, zip codes, order IDs, emails).
3. After authentication, use get_order_details to find the relevant order and its items.
4. If you need to exchange/return items, use get_product_details to find replacement variants.
5. Do NOT repeat an action that already succeeded with the same arguments.
6. If an action failed, try a different approach.
7. For exchange: you need order_id, item_ids (current items), new_item_ids (replacement variants), and payment_method_id.
8. For cancel: you need order_id and reason ("no longer needed" or "ordered by mistake").
9. For return: you need order_id and item_ids.
10. STOP QUERYING once you have all information needed for the required update actions. Do not get_product_details for items you are not exchanging.
11. If the task is to return items and you know the order_id and item_ids, execute return_delivered_order_items immediately.
12. If the task is to cancel an order and you know the order_id and reason, execute cancel_pending_order immediately.
13. Some tasks require multiple updates. Execute all requested updates, then call finish_task with empty arguments.
14. If the task asks for information to be told to the user, include a concise "message_to_user" containing the required answer. This is not a tool argument.
15. Use the EXACT parameter names from the ActionBank schema (e.g., ``zip`` not ``zip_code`` for ``find_user_id_by_name_zip``). Do not use placeholder strings like ``user_email`` or ``order_id``; always fill arguments with concrete values from the task or conversation.

Respond with JSON only:
{{
  "thought": "brief reasoning about what to do next",
  "action": "exact_action_id",
  "arguments": {{"param_name": "value"}},
  "message_to_user": "optional user-visible message"
}}"""

        user_prompt = f"""{task_info}

Execution history:
{history_text}

Current state:
- User authenticated: {state.user_authenticated}
- User ID: {state.user_id}
- Cached orders: {list(state.cached_orders.keys())}

What is the NEXT action? Extract all values from the task description. Do not repeat successful actions."""

        try:
            response = self._call_llm_json(system_prompt, user_prompt)
            return {
                "thought": response.get("thought", ""),
                "action": response.get("action", ""),
                "arguments": response.get("arguments", {}),
                "message_to_user": response.get("message_to_user", ""),
            }
        except Exception as e:
            return {
                "thought": f"LLM error: {e}",
                "action": "transfer_to_human_agents",
                "arguments": {"summary": "LLM failed to plan."},
            }
