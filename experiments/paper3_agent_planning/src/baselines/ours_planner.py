"""Ours: LLM + ActionBank + Verifier with Repair Loop."""
from __future__ import annotations

import json
from typing import Any, Dict, List

from src.state_manager import DialogueState
from src.llm_client import LLMClient
from src.action_bank import ActionBank
from src.verifier import ConstraintVerifier
from src.argument_grounder import ArgumentGrounder
from src.ontology_context import OntologyContextBuilder
from src.case_retriever import CaseRetriever
from src.task_progress import TaskProgressVerifier
from src.action_suggester import ActionSuggester
from src.goal_planner import GoalRegressionPlanner
from src.baselines.schema_baseline import SchemaPlanner, FEW_SHOT_EXAMPLE


class OursPlanner(SchemaPlanner):
    """Planner with runtime constraint verification and repair loop.
    
    Key differences from SchemaPlanner:
    1. Verifies each action before execution
    2. If verification fails, feeds violation back to LLM for repair
    3. Tracks violations and invalid actions for metrics
    """

    def __init__(
        self,
        llm: LLMClient,
        action_bank: ActionBank,
        verifier: ConstraintVerifier,
        max_repair: int = 2,
        case_retriever: CaseRetriever | None = None,
    ):
        super().__init__(llm, action_bank)
        self.verifier = verifier
        self.max_repair = max_repair
        self.grounder = ArgumentGrounder()
        self.context_builder = OntologyContextBuilder()
        self.case_retriever = case_retriever
        self.progress_verifier = TaskProgressVerifier()
        self.action_suggester = ActionSuggester()
        self.goal_planner = GoalRegressionPlanner(action_bank)

    def _build_state_guidance(self, task_info: str, state: DialogueState) -> str:
        """Build deterministic action hints from cached state.

        These hints do not execute actions. They reduce a failure mode observed
        in experiments: after a duplicate lookup is rejected, the LLM sometimes
        falls back to transfer instead of using already cached state.
        """
        lines = []
        task_l = task_info.lower()

        if state.cached_orders:
            lines.append("Cached order state, object bindings, and eligible update actions:")
        for order_id, order in state.cached_orders.items():
            status = str(order.get("status", "")).lower()
            payment_methods = []
            for p in order.get("payment_history", []):
                pm = p.get("payment_method_id")
                if pm:
                    payment_methods.append(pm)
            items = []
            for item in order.get("items", []):
                name = item.get("name", "")
                item_id = item.get("item_id", "")
                product_id = item.get("product_id", "")
                items.append(f"{name}(item_id={item_id}, product_id={product_id})")

            eligible = []
            if status == "pending":
                if any(w in task_l for w in ("cancel", "cancellation")):
                    eligible.append("cancel_pending_order")
                if any(w in task_l for w in ("address", "shipping address")):
                    eligible.append("modify_pending_order_address")
                if any(w in task_l for w in ("item", "replace", "change", "modify")):
                    eligible.append("modify_pending_order_items")
                if any(w in task_l for w in ("payment", "card")):
                    eligible.append("modify_pending_order_payment")
            elif status == "delivered":
                if any(w in task_l for w in ("return", "refund")):
                    eligible.append("return_delivered_order_items")
                if any(w in task_l for w in ("exchange", "replace", "different", "bigger", "smaller")):
                    eligible.append("exchange_delivered_order_items")

            if not eligible:
                eligible.append("no obvious terminal action from current status; gather missing information or transfer only if policy requires it")

            lines.append(
                f"- order_id={order_id}, status={status}, payment_methods={payment_methods}, "
                f"address={order.get('address', {})}, items={items[:6]}, eligible_next={eligible}"
            )

        if state.cached_users:
            lines.append("Cached user profiles:")
            for user_id, user in state.cached_users.items():
                lines.append(
                    f"- user_id={user_id}, address={user.get('address', {})}, "
                    f"payment_methods={list(user.get('payment_methods', {}).keys())}, "
                    f"orders={user.get('orders', [])}"
                )

        duplicate_reads = []
        for h in state.history:
            action = h.get("action", "")
            if action.startswith("get_") or action.startswith("find_"):
                duplicate_reads.append(f"{action}({json.dumps(h.get('arguments', {}), ensure_ascii=False)})")
        if duplicate_reads:
            lines.append("Already completed lookups; use their history results instead of repeating them:")
            for item in duplicate_reads[-8:]:
                lines.append(f"- {item}")

        if state.user_confirmed:
            lines.append("User confirmation has already been obtained for the next update action.")
        else:
            lines.append("Before cancel/return/exchange/modify, ask_for_confirmation is usually required.")

        lines.append("Do not transfer to human agents merely because a duplicate lookup was rejected; use cached results and choose a productive next action.")
        return "\n".join(lines)

    def _extract_candidates(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Normalize either a single action or a ranked candidate list."""
        candidates = response.get("candidates")
        normalized: List[Dict[str, Any]] = []
        if isinstance(candidates, list):
            for c in candidates:
                if isinstance(c, dict) and c.get("action"):
                    normalized.append({
                        "thought": c.get("thought", response.get("thought", "")),
                        "action": c.get("action", ""),
                        "arguments": c.get("arguments", {}),
                        "message_to_user": c.get("message_to_user", response.get("message_to_user", "")),
                    })
        if not normalized:
            normalized.append({
                "thought": response.get("thought", ""),
                "action": response.get("action", ""),
                "arguments": response.get("arguments", {}),
                "message_to_user": response.get("message_to_user", ""),
            })
        return normalized

    def _fallback_suggestions(self, suggestions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        always_allowed = {
            "find_user_id_by_email",
            "find_user_id_by_name_zip",
            "get_user_details",
            "get_order_details",
            "get_product_details",
            "get_item_details",
            "list_all_product_types",
            "ask_for_confirmation",
            "finish_task",
        }
        high_conf_update = {
            "modify_user_address",
            "modify_pending_order_address",
            "modify_pending_order_items",
            "modify_pending_order_payment",
            "cancel_pending_order",
            "return_delivered_order_items",
            "exchange_delivered_order_items",
        }
        eligible_updates = [
            s for s in suggestions
            if s.get("action") in high_conf_update and int(s.get("confidence", 0) or 0) >= 4
        ]
        fallback = []
        for s in suggestions:
            action = s.get("action", "")
            confidence = int(s.get("confidence", 0) or 0)
            update_allowed = (
                action in high_conf_update
                and confidence >= 4
                and len(eligible_updates) == 1
            )
            if action in always_allowed or update_allowed:
                fallback.append({
                "thought": f"Using ontology-grounded fallback suggestion: {s.get('reason', '')}",
                "action": action,
                "arguments": s.get("arguments", {}),
                "message_to_user": s.get("message_to_user", ""),
                "_suggestion_confidence": confidence,
                "_update_suggestion_fallback": action in high_conf_update,
                })
        return fallback

    def _select_fallback_suggestion(
        self,
        suggestions: List[Dict[str, Any]],
        task_info: str,
        state: DialogueState,
        db: Dict[str, Any],
        retrieved_case_ids: List[str],
        repair_trace: List[Dict[str, Any]],
    ) -> Dict[str, Any] | None:
        for suggestion in self._fallback_suggestions(suggestions):
            action_name = suggestion.get("action", "")
            raw_arguments = suggestion.get("arguments", {})
            if action_name == "finish_task":
                progress = self.progress_verifier.check_terminal(action_name, task_info, state, db)
                if not progress.passed:
                    continue
                return {
                    "thought": suggestion.get("thought", ""),
                    "action": action_name,
                    "arguments": raw_arguments,
                    "message_to_user": suggestion.get("message_to_user", ""),
                    "_retrieved_case_ids": retrieved_case_ids,
                    "_suggested_action_count": len(suggestions),
                    "_suggestion_fallback_used": True,
                    "_update_suggestion_fallback_used": bool(suggestion.get("_update_suggestion_fallback", False)),
                    "_progress_required_intents": sorted(progress.required_intents),
                    "_progress_completed_intents": sorted(progress.completed_intents),
                    "_repair_trace": repair_trace,
                }

            grounding = self.grounder.ground(action_name, raw_arguments, state, db)
            arguments = grounding.arguments
            v_result = self.verifier.verify(action_name, arguments, state, db)
            combined_violations = grounding.violations + v_result.violations
            if combined_violations:
                continue
            return {
                "thought": suggestion.get("thought", ""),
                "action": action_name,
                "arguments": arguments,
                "message_to_user": suggestion.get("message_to_user", ""),
                "_grounding_trace": grounding.changes,
                "_retrieved_case_ids": retrieved_case_ids,
                "_suggested_action_count": len(suggestions),
                "_suggestion_fallback_used": True,
                "_update_suggestion_fallback_used": bool(suggestion.get("_update_suggestion_fallback", False)),
                "_repair_trace": repair_trace,
            }
        return None

    def _try_plan_step(
        self,
        plan: List[Dict[str, Any]],
        task_info: str,
        state: DialogueState,
        db: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Attempt to execute the first admissible step of an ontology-derived plan.

        If a step is a DUPLICATE it is skipped; any other violation breaks the
        plan and forces fallback to LLM-based planning.
        """
        for step in plan:
            action_name = step["action"]
            raw_args = step.get("arguments", {})

            # Terminal-action safety check
            if action_name in {"finish_task", "transfer_to_human_agents"}:
                progress = self.progress_verifier.check_terminal(action_name, task_info, state, db)
                if progress.violations:
                    break

            grounding = self.grounder.ground(action_name, raw_args, state, db)
            args = grounding.arguments
            v_result = self.verifier.verify(action_name, args, state, db)
            combined = grounding.violations + v_result.violations

            if not combined:
                return {
                    "thought": f"Ontology-derived plan step: {action_name}",
                    "action": action_name,
                    "arguments": args,
                    "message_to_user": step.get("message_to_user", ""),
                    "_grounding_trace": grounding.changes,
                    "_from_goal_planner": True,
                    "_goal_planner_remaining": [s["action"] for s in plan[plan.index(step) + 1:]],
                }

            # Duplicate is the only skippable violation
            if not all("DUPLICATE" in v for v in combined):
                break

        return None

    def plan_next_action(self, task: Any, state: DialogueState, db: Dict[str, Any]) -> Dict[str, Any]:
        task_info = self._extract_task_info(task)

        # === Phase 1: ontology-derived goal-regression plan ===
        plan = self.goal_planner.generate_plan(task_info, state, db)
        plan_text = self.goal_planner.format_plan_for_prompt(plan)
        plan_step = self._try_plan_step(plan, task_info, state, db)
        if plan_step is not None:
            return plan_step

        # === Phase 2: LLM-based planning with plan guidance ===
        action_bank_text = self.action_bank.to_prompt_text()

        # Build execution history with results
        history_lines = []
        for h in state.history:
            if "action" in h:
                result_summary = self._format_result(h['action'], h.get('result', {}))
                history_lines.append(f"- {h['action']}({json.dumps(h.get('arguments', {}))}) -> {result_summary}")
        
        history_text = "\n".join(history_lines[-10:]) if history_lines else "No actions taken yet."
        state_guidance = self._build_state_guidance(task_info, state)
        ontology_context = self.context_builder.build(task_info, state, db)
        suggested_actions = self.action_suggester.suggest(task_info, state, db)
        suggested_actions_text = self.action_suggester.format_for_prompt(suggested_actions)
        retrieved_case_records = self.case_retriever.retrieve_records(task) if self.case_retriever else []
        retrieved_cases_text = (
            "\n\n".join(record["text"] for record in retrieved_case_records)
            if retrieved_case_records
            else "No train cases retrieved."
        )
        retrieved_case_ids = [record["task_id"] for record in retrieved_case_records]

        system_prompt = f"""You are a customer service agent for a retail store. Solve the customer's request step by step.

{FEW_SHOT_EXAMPLE}

Retrieved solved TRAIN cases for analogy. These are not the current task; reuse their action patterns, not their object IDs:
{retrieved_cases_text}

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
7a. For modify_pending_order_items, also include payment_method_id from the order's payment history.
8. For cancel: you need order_id and reason ("no longer needed" or "ordered by mistake").
9. For return: you need order_id and item_ids.
10. STOP QUERYING once you have all information needed for the required update actions.
11. Before cancel/exchange/return/modify, you MUST ask for user confirmation first (use ask_for_confirmation action).
12. If a duplicate lookup is rejected, use the cached result in history and choose a productive action; do NOT transfer only because of duplicate rejection.
13. If order.status is pending, do not return/exchange it; consider cancel or modify actions.
14. If order.status is delivered, do not cancel or modify pending-order fields; consider return/exchange actions.
15. Transfer to human agents only when the policy or task explicitly requires human escalation.
16. Some tasks require multiple updates. Execute all requested updates, then call finish_task with empty arguments.
17. Use cached object bindings for address, payment_method_id, order_id, item_ids, and new_item_ids; do not invent IDs.
18. If the task asks for information to be told to the user, include a concise "message_to_user" containing the required answer. This is not a tool argument.
19. Use the EXACT parameter names from the ActionBank schema (e.g., ``zip`` not ``zip_code`` for ``find_user_id_by_name_zip``). Do not use placeholder strings like ``user_email`` or ``order_id``; always fill arguments with concrete values from the task or conversation.

Respond with JSON only:
{{
  "thought": "brief reasoning about what to do next",
  "action": "exact_action_id",
  "arguments": {{"param_name": "value"}},
  "message_to_user": "optional user-visible message",
  "candidates": [
    {{"thought": "best admissible next step", "action": "exact_action_id", "arguments": {{"param_name": "value"}}, "message_to_user": "optional user-visible message"}},
    {{"thought": "fallback if the first is not admissible", "action": "exact_action_id", "arguments": {{"param_name": "value"}}, "message_to_user": "optional user-visible message"}}
  ]
}}"""

        user_prompt = f"""{task_info}

Execution history:
{history_text}

Current state:
- User authenticated: {state.user_authenticated}
- User ID: {state.user_id}
- Cached orders: {list(state.cached_orders.keys())}

Ontology-grounded object candidates:
{ontology_context}

Ontology-grounded recommended next actions:
{suggested_actions_text}

State-derived action guidance:
{state_guidance}

{plan_text}

        What is the NEXT action? Extract all values from the task description. Do not repeat successful actions."""

        # Try with repair loop (repairs don't count against step budget)
        repair_trace = []
        for attempt in range(self.max_repair + 1):
            try:
                current_prompt = user_prompt
                for json_attempt in range(2):
                    try:
                        response = self.llm.chat_json(system_prompt, current_prompt)
                        break
                    except Exception:
                        if json_attempt == 0:
                            current_prompt = (
                                user_prompt
                                + "\n\nREMINDER: Return ONLY a single valid JSON object. "
                                "Do not include any explanatory text before or after the JSON."
                            )
                            continue
                        raise
                candidates = self._extract_candidates(response)
                terminal_candidates = []
                rejected_this_attempt = []

                for candidate in candidates:
                    action_name = candidate.get("action", "")
                    raw_arguments = candidate.get("arguments", {})
                    if action_name in {"transfer_to_human_agents", "finish_task"}:
                        terminal_candidates.append(candidate)
                        continue

                    grounding = self.grounder.ground(action_name, raw_arguments, state, db)
                    arguments = grounding.arguments
                    v_result = self.verifier.verify(action_name, arguments, state, db)
                    combined_violations = grounding.violations + v_result.violations
                    if not combined_violations:
                        return {
                            "thought": candidate.get("thought", response.get("thought", "")),
                            "action": action_name,
                            "arguments": arguments,
                            "message_to_user": candidate.get("message_to_user", ""),
                            "_grounding_trace": grounding.changes,
                            "_retrieved_case_ids": retrieved_case_ids,
                            "_suggested_action_count": len(suggested_actions),
                            "_repair_trace": repair_trace,
                        }

                    rejected = {
                        "attempt": attempt,
                        "rejected_action": action_name,
                        "rejected_arguments": raw_arguments,
                        "grounded_arguments": arguments,
                        "grounding_changes": grounding.changes,
                        "violations": combined_violations,
                    }
                    repair_trace.append(rejected)
                    rejected_this_attempt.append(rejected)

                for terminal_candidate in terminal_candidates:
                    action_name = terminal_candidate.get("action", "")
                    progress = self.progress_verifier.check_terminal(action_name, task_info, state, db)
                    progress_violations = list(progress.violations)
                    if action_name == "transfer_to_human_agents" and self._fallback_suggestions(suggested_actions):
                        progress_violations.append(
                            "PROGRESS: transfer_to_human_agents while safe ontology-grounded fallback actions are available"
                        )
                    if not progress_violations and not rejected_this_attempt:
                        return {
                            "thought": terminal_candidate.get("thought", response.get("thought", "")),
                            "action": action_name,
                            "arguments": terminal_candidate.get("arguments", {}),
                            "message_to_user": terminal_candidate.get("message_to_user", ""),
                            "_retrieved_case_ids": retrieved_case_ids,
                            "_suggested_action_count": len(suggested_actions),
                            "_progress_required_intents": sorted(progress.required_intents),
                            "_progress_completed_intents": sorted(progress.completed_intents),
                            "_repair_trace": repair_trace,
                        }
                    rejected = {
                        "attempt": attempt,
                        "rejected_action": action_name,
                        "rejected_arguments": terminal_candidate.get("arguments", {}),
                        "grounded_arguments": terminal_candidate.get("arguments", {}),
                        "grounding_changes": [],
                        "violations": progress_violations or [
                            "PROGRESS: terminal action deferred until non-terminal candidates are resolved"
                        ],
                    }
                    repair_trace.append(rejected)
                    rejected_this_attempt.append(rejected)

                if rejected_this_attempt:
                    fallback = self._select_fallback_suggestion(
                        suggested_actions, task_info, state, db, retrieved_case_ids, repair_trace
                    )
                    if fallback:
                        return fallback

                violations_text = "\n".join(
                    f"- {r['rejected_action']}({json.dumps(r['rejected_arguments'], ensure_ascii=False)}): {r['violations']}"
                    for r in rejected_this_attempt
                )
                user_prompt += f"""

Candidate actions were REJECTED by the ontology-grounded verifier/progress checker:
{violations_text}

State-derived action guidance:
{self._build_state_guidance(task_info, state)}

Ontology-grounded object candidates:
{self.context_builder.build(task_info, state, db)}

Ontology-grounded recommended next actions:
{self.action_suggester.format_for_prompt(self.action_suggester.suggest(task_info, state, db))}

Please propose a DIFFERENT productive action that satisfies all constraints. Provide at least two candidates. If a candidate was a duplicate lookup, use the cached history result instead of transferring to a human agent. Do not call finish_task until all required intents are completed."""
                
                # Note: We do NOT record the rejected action in state.history
                # because it was never actually executed. This prevents repair
                # from consuming the step budget.
                
            except Exception as e:
                if attempt == self.max_repair:
                    return {
                        "thought": f"LLM error after {self.max_repair} repair attempts: {e}",
                        "action": "transfer_to_human_agents",
                        "arguments": {"summary": "LLM failed to plan."},
                        "message_to_user": "",
                        "_retrieved_case_ids": retrieved_case_ids,
                        "_suggested_action_count": len(suggested_actions),
                        "_repair_trace": repair_trace,
                    }
        
        # Max repairs reached
        return {
            "thought": f"Max repair attempts ({self.max_repair}) reached. Could not find valid action.",
            "action": "transfer_to_human_agents",
            "arguments": {"summary": "Could not find valid action after multiple attempts."},
            "message_to_user": "",
            "_grounding_trace": [],
            "_retrieved_case_ids": retrieved_case_ids,
            "_suggested_action_count": len(suggested_actions),
            "_repair_trace": repair_trace,
        }
