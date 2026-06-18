#!/usr/bin/env python3
"""Tau2-compatible schema and ontology-guided agent entrypoint.

This script is intentionally separate from the local runner. The local runner is
useful for debugging action selection, but paper-grade tau-bench task
performance must be produced by the official tau2/tau3 orchestrator and
evaluator. This agent registers a custom half-duplex agent with tau2 and lets
the official environment execute tools and calculate rewards.

Run from an environment where tau2 is installed:

    python experiments/paper3_agent_planning/tau2_ontology_agent.py \
      --domain retail \
      --agent-kind ontology \
      --agent-model gemma4-31b \
      --agent-base-url http://172.16.22.79:9999/v1 \
      --user-llm gpt-4.1 \
      --task-split-name base \
      --save-to ontology_agent_retail
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any, Dict, List, Optional

BASE_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / "src"))

from llm_client import OpenAIClient  # noqa: E402
from action_bank import ActionBank  # noqa: E402
from argument_grounder import ArgumentGrounder  # noqa: E402
from ontology_repair import OntologyRepairPlanner  # noqa: E402
from runtime_ontology import RuntimeOntologyState, reconstruct_runtime_state  # noqa: E402
from tau2_admissibility import (  # noqa: E402
    Tau2AdmissibilityChecker,
    extract_history_tool_calls,
    repair_hints,
)


ACTION_BANK_PATH = BASE_DIR / "data/action_bank/retail_action_bank.json"

# Common parameter-name hallucinations produced by LLMs when calling official tau2 tools.
PARAMETER_NAME_ALIASES: Dict[str, Dict[str, str]] = {
    "find_user_id_by_name_zip": {"zip_code": "zip", "zipcode": "zip", "postal_code": "zip"},
    "get_order_details": {"order_number": "order_id", "orderId": "order_id"},
    "get_user_details": {"userId": "user_id", "user_id_number": "user_id"},
    "cancel_pending_order": {"order_number": "order_id", "orderId": "order_id"},
    "modify_pending_order_address": {"order_number": "order_id", "orderId": "order_id"},
    "modify_pending_order_items": {"order_number": "order_id", "orderId": "order_id"},
    "modify_pending_order_payment": {"order_number": "order_id", "orderId": "order_id"},
    "return_delivered_order_items": {"order_number": "order_id", "orderId": "order_id"},
    "exchange_delivered_order_items": {"order_number": "order_id", "orderId": "order_id"},
}

# Values that are clearly placeholders and must be rejected.
PLACEHOLDER_VALUES = {
    "user_email", "email_address", "unknown", "none", "n/a", "null", "",
    "order_id", "order_number", "user_id", "item_id", "product_id",
    "first_name", "last_name", "phone_number", "address", "reason",
}

# Regex patterns to extract concrete values from conversation text.
VALUE_EXTRACTION_PATTERNS = {
    "email": re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", re.IGNORECASE
    ),
    "order_id": re.compile(r"\#?W\d{7,10}\b", re.IGNORECASE),
}


class Tau2ArgumentNormalizer:
    """Normalize LLM-proposed tool arguments against official tau2 tool schemas.

    The local ActionBank and the official tau2 tool schemas are broadly aligned,
    but LLMs sometimes hallucinate parameter names (e.g., ``zip_code`` instead of
    ``zip``) or emit placeholder strings (e.g., ``user_email``). This normalizer
    fixes those issues before the candidate reaches the admissibility gate or the
    official tool executor.
    """

    def __init__(self, tools: list[Any]):
        self.tool_schemas: Dict[str, Dict[str, Any]] = {}
        for tool in tools:
            name = getattr(tool, "name", "")
            if not name:
                continue
            schema = (
                getattr(tool, "parameters", None)
                or getattr(tool, "args_schema", None)
                or getattr(tool, "input_schema", None)
                or {}
            )
            # Handle OpenAI-style function schema wrapping.
            if isinstance(schema, dict) and "function" in schema:
                schema = schema["function"]
            if isinstance(schema, dict) and "parameters" in schema:
                schema = schema["parameters"]
            self.tool_schemas[name] = schema

    def normalize(
        self,
        action: str,
        arguments: Dict[str, Any],
        context_text: str,
    ) -> Dict[str, Any]:
        """Return a normalized copy of the candidate arguments."""
        if action not in self.tool_schemas:
            return dict(arguments)

        schema = self.tool_schemas[action]
        props: Dict[str, Any] = {}
        if isinstance(schema, dict):
            props = schema.get("properties", {})
            if not props and "properties" in schema.get("parameters", {}):
                props = schema["parameters"]["properties"]

        valid_keys = set(props.keys())
        aliases = PARAMETER_NAME_ALIASES.get(action, {})

        normalized: Dict[str, Any] = {}
        for raw_key, value in (arguments or {}).items():
            key = aliases.get(raw_key, raw_key)
            if key not in valid_keys and valid_keys:
                # Fuzzy fallback: accept an alias if it is a substring of a valid key.
                for valid in valid_keys:
                    if raw_key.lower() in valid.lower() or valid.lower() in raw_key.lower():
                        key = valid
                        break
            normalized[key] = value

        # Fill missing parameters by extracting values from conversation history.
        for key in valid_keys:
            if key in normalized and normalized[key] not in (None, ""):
                continue
            extracted = self._extract_from_context(key, context_text)
            if extracted is not None:
                normalized[key] = extracted

        return normalized

    def detect_placeholders(self, action: str, arguments: Dict[str, Any]) -> List[str]:
        """Return violations for placeholder arguments that need real values."""
        violations: List[str] = []
        schema = self.tool_schemas.get(action, {})
        props: Dict[str, Any] = {}
        if isinstance(schema, dict):
            props = schema.get("properties", {})
            if not props and "properties" in schema.get("parameters", {}):
                props = schema["parameters"]["properties"]

        required = set()
        if isinstance(schema, dict):
            required = set(schema.get("required", []))
            if not required and "required" in schema.get("parameters", {}):
                required = set(schema["parameters"]["required"])

        for key, value in arguments.items():
            str_value = str(value).strip().lower()
            if str_value in PLACEHOLDER_VALUES:
                violations.append(f"PLACEHOLDER_VALUE: {action}.{key}={value}")
            if key in required and value in (None, ""):
                violations.append(f"MISSING_PARAMETER: {action}.{key}")

        return violations

    def _extract_from_context(self, key: str, context_text: str) -> Any:
        if key == "email":
            m = VALUE_EXTRACTION_PATTERNS["email"].search(context_text)
            return m.group(0) if m else None
        if key == "order_id":
            ms = VALUE_EXTRACTION_PATTERNS["order_id"].findall(context_text)
            # Prefer the most recently mentioned order id.
            return ms[-1] if ms else None
        if key in ("first_name", "last_name"):
            # Best-effort: look for "my name is X Y" patterns.
            pattern = re.compile(
                r"my\s+name\s+is\s+(?P<first>\w+)(?:\s+(?P<last>\w+))?",
                re.IGNORECASE,
            )
            m = pattern.search(context_text)
            if m:
                if key == "first_name":
                    return m.group("first")
                if key == "last_name" and m.group("last"):
                    return m.group("last")
        return None




def stringify_tool(tool: Any) -> str:
    name = getattr(tool, "name", "")
    description = getattr(tool, "description", "") or getattr(tool, "doc", "")
    parameters = (
        getattr(tool, "parameters", None)
        or getattr(tool, "args_schema", None)
        or getattr(tool, "input_schema", None)
        or {}
    )
    try:
        parameter_text = json.dumps(parameters, ensure_ascii=False, default=str)
    except TypeError:
        parameter_text = str(parameters)
    return f"- {name}: {description}\n  parameters={parameter_text}"


def message_to_text(message: Any) -> str:
    role = getattr(message, "role", "")
    content = getattr(message, "content", None)
    tool_calls = getattr(message, "tool_calls", None)
    if content:
        return f"{role}: {content}"
    if tool_calls:
        return f"{role}: tool_calls={tool_calls}"
    return f"{role}: {message}"


class OntologyAgentState:
    def __init__(self, messages: Optional[list[Any]] = None):
        self.messages = list(messages) if messages else []


def action_bank_prompt_text(action_bank: ActionBank | None) -> str:
    if action_bank is None:
        return ""
    return action_bank.to_prompt_text()


def load_action_bank(domain: str) -> ActionBank | None:
    if domain != "retail" or not ACTION_BANK_PATH.exists():
        return None
    return ActionBank.from_json(ACTION_BANK_PATH)


def _normalize_option_text(text: str) -> str:
    normalized = text.lower()
    normalized = normalized.replace("google home", "google assistant")
    normalized = normalized.replace("homekit", "apple homekit")
    normalized = normalized.replace("small", "s")
    normalized = normalized.replace("medium", "m")
    normalized = normalized.replace("large", "l")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _option_alias_match(option_value: str, context_text: str) -> bool:
    aliases = {
        "s": (" size s ", " small "),
        "m": (" size m ", " medium "),
        "l": (" size l ", " large "),
        "google assistant": (" google home ", " google assistant "),
        "apple homekit": (" apple homekit ", " homekit "),
        "v neck": (" v neck ", " v-neck "),
        "crew neck": (" crew neck ", " crew-neck "),
        "full size": (" full size ", " full-size "),
    }
    padded = f" {context_text} "
    for canonical, candidates in aliases.items():
        if option_value == canonical and any(candidate in padded for candidate in candidates):
            return True
    return False


def uses_ontology_prompt(agent_kind: str) -> bool:
    return agent_kind in {
        "ontology_prompt",
        "state_only",
        "ontology_lite",
        "typed_admissibility",
        "ontology_full",
        "ontology",
    }


def uses_runtime_ontology_state(agent_kind: str) -> bool:
    return agent_kind in {
        "state_only",
        "ontology_lite",
        "typed_admissibility",
        "ontology_full",
        "ontology",
    }


def uses_admissibility_gate(agent_kind: str) -> bool:
    return agent_kind in {
        "ontology_lite",
        "typed_admissibility",
        "ontology_full",
        "ontology",
    }


def uses_full_conditions(agent_kind: str) -> bool:
    return agent_kind in {"typed_admissibility", "ontology_full", "ontology"}


def uses_ontology_repair(agent_kind: str) -> bool:
    return agent_kind in {"ontology_full", "ontology"}


def build_ontology_section(
    agent_kind: str,
    action_bank_text: str,
    runtime_state_text: str,
) -> str:
    if not uses_ontology_prompt(agent_kind):
        return ""
    lines = [
        "Ontology action layer:",
        action_bank_text or "No local ActionBank available for this domain.",
    ]
    if uses_runtime_ontology_state(agent_kind):
        lines.extend([
            "",
            "Runtime ontology state extracted from prior tool results:",
            runtime_state_text,
            "",
            "Use the runtime ontology state as the source of truth for user_id, "
            "order_id, item_id, product_id, product variants, payment_method_id, "
            "and order status.",
        ])
    return "\n".join(lines)


def premature_response_violations(
    candidate: Dict[str, Any],
    rejected: List[Dict[str, Any]],
    gate_enabled: bool,
    context_text: str = "",
) -> List[str]:
    """Reject generic user responses when repairable actions are still pending."""
    if not gate_enabled:
        return []
    action = str(candidate.get("action", "") or "")
    if action not in {"respond_to_user", "transfer_to_human_agents"}:
        return []
    message = str(candidate.get("message_to_user", "") or "").lower()
    if action == "transfer_to_human_agents":
        lowered_context = context_text.lower()
        explicit_transfer_request = any(
            marker in lowered_context
            for marker in (
                "transfer me",
                "human agent",
                "real person",
                "supervisor",
                "someone else",
                "another department",
            )
        )
        if explicit_transfer_request:
            return []
        return ["PREMATURE_RESPONSE: transfer is not admissible until prerequisite actions have been attempted or policy explicitly requires transfer"]
    if not message:
        return []
    has_repair_path = any(
        item.get("repair_hints")
        or item.get("ontology_repair_candidate")
        or item.get("deterministic_repair_candidate")
        for item in rejected
    )
    generic_markers = (
        "cannot complete",
        "can't complete",
        "unable to complete",
        "available tools",
        "transfer this request",
        "human agent",
        "human assistance",
        "planning failed",
        "too many requests",
        "http error 429",
    )
    if any(marker in message for marker in generic_markers) and (has_repair_path or not rejected):
        return ["PREMATURE_RESPONSE: repairable prerequisites remain; do not end the task with a generic response"]
    return []


def build_agent_class(agent_kind: str):
    from tau2.agent.base_agent import HalfDuplexAgent
    from tau2.data_model.message import AssistantMessage, Message, ToolCall

    class JsonTau2Agent(HalfDuplexAgent[OntologyAgentState]):
        """Half-duplex tau2 agent using JSON planning over official tau2 tools."""

        def __init__(
            self,
            tools: list[Any],
            domain_policy: str,
            llm: str = "gemma4-31b",
            llm_args: Optional[dict[str, Any]] = None,
            base_url: str = "http://172.16.22.79:9999/v1",
            api_key: str = "EMPTY",
            domain: str = "retail",
        ):
            super().__init__(tools=tools, domain_policy=domain_policy)
            self.llm = OpenAIClient(model=llm, base_url=base_url, api_key=api_key)
            self.llm_args = llm_args or {}
            self.agent_kind = agent_kind
            self.tool_names = {getattr(tool, "name", "") for tool in tools}
            self.tool_text = "\n".join(stringify_tool(tool) for tool in tools)
            self.action_bank = load_action_bank(domain)
            self.action_bank_text = action_bank_prompt_text(self.action_bank)
            self.argument_grounder = ArgumentGrounder()
            self.repair_planner = (
                OntologyRepairPlanner(self.action_bank, self.tool_names)
                if self.action_bank is not None
                else None
            )
            self.admissibility_checker = Tau2AdmissibilityChecker(
                self.tool_names,
                self.action_bank,
                enabled=uses_admissibility_gate(self.agent_kind),
                enforce_conditions=uses_full_conditions(self.agent_kind),
            )
            self.argument_normalizer = Tau2ArgumentNormalizer(tools)

        def get_init_state(self, message_history: Optional[list[Message]] = None) -> OntologyAgentState:
            return OntologyAgentState(message_history)

        def _extract_candidates(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
            candidates = response.get("candidates")
            normalized: List[Dict[str, Any]] = []
            if isinstance(candidates, list):
                for candidate in candidates:
                    if isinstance(candidate, dict) and candidate.get("action"):
                        normalized.append({
                            "thought": candidate.get("thought", response.get("thought", "")),
                            "action": str(candidate.get("action", "") or ""),
                            "arguments": candidate.get("arguments", {}) if isinstance(candidate.get("arguments", {}), dict) else {},
                            "message_to_user": candidate.get("message_to_user", response.get("message_to_user", "")),
                        })
            if not normalized:
                normalized.append({
                    "thought": response.get("thought", ""),
                    "action": str(response.get("action", "") or ""),
                    "arguments": response.get("arguments", {}) if isinstance(response.get("arguments", {}), dict) else {},
                    "message_to_user": response.get("message_to_user", ""),
                })
            return normalized

        def _history_tool_calls(self, state: OntologyAgentState) -> List[Dict[str, Any]]:
            return extract_history_tool_calls(state.messages)

        def _verify_candidate(
            self,
            candidate: Dict[str, Any],
            state: OntologyAgentState,
            context_text: str,
            runtime_state: RuntimeOntologyState,
        ) -> List[str]:
            return self.admissibility_checker.verify_candidate(
                candidate,
                self._history_tool_calls(state),
                context_text=context_text,
                runtime_state=runtime_state,
            )

        def _ground_candidate(
            self,
            candidate: Dict[str, Any],
            runtime_state: RuntimeOntologyState,
            context_text: str,
        ) -> None:
            action = str(candidate.get("action", "") or "")
            if action not in self.tool_names:
                return
            arguments = candidate.get("arguments", {})
            if not isinstance(arguments, dict):
                arguments = {}
            changes: List[str] = []
            arguments = self.argument_normalizer.normalize(action, arguments, context_text)
            arguments, weak_changes = self._weak_ground_lookup_arguments(action, arguments)
            changes.extend(weak_changes)
            arguments, local_changes = self._ground_from_runtime_state(
                action,
                arguments,
                runtime_state,
                context_text,
            )
            changes.extend(local_changes)
            schema = self.action_bank.get(action) if self.action_bank is not None else None
            if schema is None or getattr(schema, "grounding_mode", "strong") != "weak":
                grounded = self.argument_grounder.ground(
                    action,
                    arguments,
                    runtime_state.to_dialogue_state(),
                    runtime_state.to_grounding_db(),
                    schema=schema,
                )
                arguments = grounded.arguments
                changes.extend(grounded.changes)
                if grounded.violations:
                    candidate.setdefault("_grounding_violations", []).extend(grounded.violations)
            candidate["arguments"] = arguments
            if changes:
                candidate.setdefault("_grounding_changes", []).extend(changes)
                runtime_state.grounding_changes.extend(changes)

        def _weak_ground_lookup_arguments(
            self,
            action: str,
            arguments: Dict[str, Any],
        ) -> tuple[Dict[str, Any], List[str]]:
            grounded = dict(arguments)
            changes: List[str] = []
            if action == "get_order_details" and grounded.get("order_id"):
                order_id = str(grounded["order_id"])
                if re.fullmatch(r"W\d{7,10}", order_id, flags=re.IGNORECASE):
                    grounded["order_id"] = f"#{order_id}"
                    changes.append(f"order_id:{order_id}->{grounded['order_id']}")
            return grounded, changes

        def _ground_from_runtime_state(
            self,
            action: str,
            arguments: Dict[str, Any],
            runtime_state: RuntimeOntologyState,
            context_text: str,
        ) -> tuple[Dict[str, Any], List[str]]:
            grounded = dict(arguments)
            changes: List[str] = []
            if action in {"get_user_details", "modify_user_address"} and runtime_state.user_id:
                if grounded.get("user_id") != runtime_state.user_id:
                    changes.append(f"user_id:{grounded.get('user_id')}->{runtime_state.user_id}")
                    grounded["user_id"] = runtime_state.user_id

            order = runtime_state.orders.get(str(grounded.get("order_id") or ""))
            if action in {
                "modify_pending_order_items",
                "return_delivered_order_items",
                "exchange_delivered_order_items",
            } and not grounded.get("payment_method_id"):
                payment_id = self._single_payment_method(order, runtime_state)
                if payment_id:
                    grounded["payment_method_id"] = payment_id
                    changes.append(f"payment_method_id:<missing>->{payment_id}")

            if action in {"modify_pending_order_items", "exchange_delivered_order_items"}:
                grounded, variant_changes = self._ground_new_item_ids(
                    grounded,
                    order,
                    runtime_state,
                    context_text,
                )
                changes.extend(variant_changes)
            return grounded, changes

        def _single_payment_method(
            self,
            order: Optional[Dict[str, Any]],
            runtime_state: RuntimeOntologyState,
        ) -> str:
            candidates: List[str] = []
            if order:
                for payment in order.get("payment_history", []) or []:
                    payment_id = payment.get("payment_method_id")
                    if payment_id and payment_id not in candidates:
                        candidates.append(payment_id)
            for payment_id in runtime_state.payment_methods:
                if payment_id not in candidates:
                    candidates.append(payment_id)
            return candidates[0] if len(candidates) == 1 else ""

        def _ground_new_item_ids(
            self,
            arguments: Dict[str, Any],
            order: Optional[Dict[str, Any]],
            runtime_state: RuntimeOntologyState,
            context_text: str,
        ) -> tuple[Dict[str, Any], List[str]]:
            if not order:
                return arguments, []
            item_ids = arguments.get("item_ids")
            if isinstance(item_ids, str):
                item_ids = [item_ids]
            if not isinstance(item_ids, list) or not item_ids:
                return arguments, []
            current_new = arguments.get("new_item_ids")
            if isinstance(current_new, str):
                current_new = [current_new]

            order_items = {str(item.get("item_id")): item for item in order.get("items", []) or []}
            if isinstance(current_new, list) and len(current_new) == len(item_ids):
                invalid_pairs = []
                for source_item_id, new_item_id in zip(item_ids, current_new):
                    source_item = order_items.get(str(source_item_id))
                    expected_product_id = str((source_item or {}).get("product_id") or "")
                    actual_product_id = self._variant_product_id(str(new_item_id), runtime_state)
                    if expected_product_id and actual_product_id == expected_product_id:
                        continue
                    invalid_pairs.append((source_item_id, new_item_id))
                if not invalid_pairs:
                    return arguments, []

            inferred: List[str] = []
            for item_id in item_ids:
                source_item = order_items.get(str(item_id))
                if not source_item:
                    return arguments, []
                product_id = str(source_item.get("product_id") or "")
                product = runtime_state.products.get(product_id)
                if not product:
                    return arguments, []
                variant_id = self._select_variant_id(product, str(source_item.get("item_id")), context_text)
                if not variant_id:
                    return arguments, []
                inferred.append(variant_id)
            grounded = dict(arguments)
            grounded["item_ids"] = [str(item_id) for item_id in item_ids]
            grounded["new_item_ids"] = inferred
            return grounded, [f"new_item_ids:inferred->{inferred}"]

        def _variant_product_id(self, item_id: str, runtime_state: RuntimeOntologyState) -> str:
            for product_id, product in runtime_state.products.items():
                if item_id in (product.get("variants") or {}):
                    return str(product_id)
            return ""

        def _select_variant_id(self, product: Dict[str, Any], current_item_id: str, context_text: str) -> str:
            text = _normalize_option_text(context_text)
            best_id = ""
            best_score = 0
            for item_id, variant in (product.get("variants") or {}).items():
                if str(item_id) == str(current_item_id):
                    continue
                if variant.get("available") is False:
                    continue
                score = 0
                for value in (variant.get("options") or {}).values():
                    normalized = _normalize_option_text(str(value))
                    if normalized and normalized in text:
                        score += 3
                    elif _option_alias_match(normalized, text):
                        score += 2
                if score > best_score:
                    best_id = str(item_id)
                    best_score = score
            return best_id if best_score > 0 else ""

        def _assistant_message(
            self,
            response: Dict[str, Any],
            raw_response: Dict[str, Any],
            rejected: Optional[List[Dict[str, Any]]] = None,
        ):
            action = str(response.get("action", "") or "")
            arguments = response.get("arguments", {}) if isinstance(response.get("arguments", {}), dict) else {}
            message_to_user = str(response.get("message_to_user", "") or "")
            gate_trace = {
                "enabled": uses_admissibility_gate(self.agent_kind),
                "condition_enforcement": uses_full_conditions(self.agent_kind),
                "runtime_state_exposed": uses_runtime_ontology_state(self.agent_kind),
                "repair_enabled": uses_ontology_repair(self.agent_kind),
                "selected_action": action,
                "selected_arguments": arguments,
                "rejected_candidates": rejected or [],
                "rejection_count": len(rejected or []),
                "repair_attempt_count": len({item.get("attempt") for item in rejected or []}),
                "grounding_changes": response.get("_grounding_changes", []),
                "grounding_violations": response.get("_grounding_violations", []),
            }

            if action in self.tool_names:
                return AssistantMessage.text(
                    "",
                    tool_calls=[ToolCall(name=action, arguments=arguments, requestor="assistant")],
                    raw_data={
                        "ontology_agent_response": raw_response,
                        "selected_candidate": response,
                        "agent_kind": self.agent_kind,
                        "ontology_gate": gate_trace,
                    },
                )
            return AssistantMessage.text(
                message_to_user or "I cannot complete this request with the available tools.",
                raw_data={
                    "ontology_agent_response": raw_response,
                    "selected_candidate": response,
                    "agent_kind": self.agent_kind,
                    "ontology_gate": gate_trace,
                },
            )

        def generate_next_message(self, message: Any, state: OntologyAgentState):
            state.messages.append(message)
            history = "\n".join(message_to_text(m) for m in state.messages[-12:])
            runtime_state = reconstruct_runtime_state(state.messages, self.action_bank)
            runtime_state_text = runtime_state.to_prompt_text()
            ontology_section = build_ontology_section(
                self.agent_kind,
                self.action_bank_text,
                runtime_state_text,
            )
            system_prompt = f"""You are a customer-service agent evaluated by official tau2.

Follow the domain policy exactly. Use tools only when their preconditions are
semantically satisfied. Prefer productive tool calls over repeated lookups.
Before mutating customer records, obtain any confirmation required by policy.
If the task requires communicating a value to the user, respond with text that
contains that exact value. Do not output both text and a tool call in the same
turn.

CRITICAL: Use the exact parameter names shown in each tool's parameters block
(for example, use ``zip`` not ``zip_code`` for ``find_user_id_by_name_zip``).
Do not use placeholder strings such as ``user_email``, ``order_id``, or
``unknown``; always fill arguments with concrete values taken from the
conversation or tool results.

Domain policy:
{self.domain_policy}

Available tools:
{self.tool_text}

{ontology_section}

Return JSON only. Do not include any markdown code blocks, explanations, or
conversational text outside the JSON object. Your entire response must be a
single valid JSON object matching this exact schema:

{{
  "thought": "brief private reasoning",
  "action": "tool name, or respond_to_user",
  "arguments": {{"param": "value"}},
  "message_to_user": "text to send when action is respond_to_user",
  "candidates": [
    {{"thought": "best next action", "action": "tool name or respond_to_user", "arguments": {{}}, "message_to_user": ""}},
    {{"thought": "fallback action", "action": "tool name or respond_to_user", "arguments": {{}}, "message_to_user": ""}}
  ]
}}

Example for looking up an order by email:
{{
  "thought": "I need to authenticate the user first.",
  "action": "find_user_id_by_email",
  "arguments": {{"email": "alice@example.com"}},
  "message_to_user": "",
  "candidates": []
}}"""
            user_prompt = f"""Conversation so far:
{history}

Choose the next single assistant action."""
            response: Dict[str, Any] = {}
            rejected: List[Dict[str, Any]] = []
            for attempt in range(4):
                current_prompt = user_prompt
                # Retry once on JSON parse failure before giving up.
                for json_attempt in range(3):
                    try:
                        response = self.llm.chat_json(system_prompt, current_prompt, temperature=0.0)
                        break
                    except Exception as exc:
                        if json_attempt < 2:
                            current_prompt = (
                                user_prompt
                                + "\n\nREMINDER: Return ONLY a single valid JSON object. "
                                "Do not include any explanatory text before or after the JSON."
                            )
                            continue
                        response = {
                            "action": "respond_to_user",
                            "arguments": {},
                            "message_to_user": "I need a moment to continue checking the account details.",
                            "_planning_error": str(exc),
                        }
                for candidate in self._extract_candidates(response):
                    action = str(candidate.get("action", "") or "")
                    if action in self.tool_names and uses_admissibility_gate(self.agent_kind):
                        self._ground_candidate(candidate, runtime_state, history)
                        placeholder_violations = self.argument_normalizer.detect_placeholders(
                            action, candidate["arguments"]
                        )
                        # Promote placeholders to hard violations so the repair loop fires.
                        if placeholder_violations:
                            candidate["_placeholder_violations"] = placeholder_violations
                    violations = self._verify_candidate(candidate, state, history, runtime_state)
                    violations.extend(
                        candidate.get("_placeholder_violations", [])
                    )
                    violations.extend(
                        candidate.get("_grounding_violations", [])
                    )
                    violations.extend(
                        premature_response_violations(
                            candidate,
                            rejected,
                            uses_admissibility_gate(self.agent_kind),
                            history,
                        )
                    )
                    if not violations:
                        assistant_message = self._assistant_message(candidate, response, rejected)
                        state.messages.append(assistant_message)
                        return assistant_message, state
                    rejected.append({
                        "attempt": attempt,
                        "candidate": candidate,
                        "violations": violations,
                        "repair_hints": [],
                    })
                    repair_candidate = (
                        self.repair_planner.plan(
                            candidate,
                            violations,
                            runtime_state,
                            history,
                        )
                        if self.repair_planner is not None
                        and uses_ontology_repair(self.agent_kind)
                        else None
                    )
                    if repair_candidate is not None:
                        rejected[-1]["repair_hints"] = [
                            "Acquire missing predicate "
                            f"`{repair_candidate.get('_missing_predicate', '')}` "
                            f"through ontology provider "
                            f"`{repair_candidate.get('_provider_action', '')}`."
                        ]
                    else:
                        rejected[-1]["repair_hints"] = repair_hints(candidate, violations)
                    if repair_candidate is not None:
                        if uses_admissibility_gate(self.agent_kind):
                            self._ground_candidate(repair_candidate, runtime_state, history)
                        repair_violations = self._verify_candidate(
                            repair_candidate,
                            state,
                            history,
                            runtime_state,
                        )
                        repair_violations.extend(repair_candidate.get("_grounding_violations", []))
                        rejected[-1]["ontology_repair_candidate"] = repair_candidate
                        rejected[-1]["ontology_repair_violations"] = repair_violations
                        if not repair_violations:
                            assistant_message = self._assistant_message(repair_candidate, response, rejected)
                            state.messages.append(assistant_message)
                            return assistant_message, state
                if not uses_admissibility_gate(self.agent_kind):
                    break
                if not uses_ontology_repair(self.agent_kind):
                    break
                violation_text = "\n".join(
                    f"- {item['candidate'].get('action')}({json.dumps(item['candidate'].get('arguments', {}), ensure_ascii=False)}): "
                    f"violations={item['violations']}; repair_hints={item.get('repair_hints', [])}"
                    for item in rejected[-4:]
                )
                user_prompt += f"""

The ontology-grounded admissibility checker rejected the previous candidates:
{violation_text}

Choose the next candidate by following the repair hints. Prefer prerequisite
lookup, authentication, confirmation, or communication actions over repeating
the rejected action. Use cached tool results from the conversation when
available. Do not transfer to a human agent merely because an internal planning
attempt failed; choose a valid next tool call or ask the user for the specific
missing value."""

            fallback = {
                "action": "respond_to_user",
                "arguments": {},
                "message_to_user": "I cannot complete this request with the available tools.",
                "_rejected_candidates": rejected,
            }
            assistant_message = self._assistant_message(fallback, response, rejected)
            state.messages.append(assistant_message)
            return assistant_message, state

    return JsonTau2Agent


def create_ontology_guided_agent(tools, domain_policy, **kwargs):
    agent_cls = build_agent_class("ontology_full")
    llm_args = kwargs.get("llm_args") or {}
    return agent_cls(
        tools=tools,
        domain_policy=domain_policy,
        llm=kwargs.get("llm") or kwargs.get("agent_llm") or "gemma4-31b",
        llm_args=llm_args,
        base_url=llm_args.get("base_url") or kwargs.get("base_url") or "http://172.16.22.79:9999/v1",
        api_key=llm_args.get("api_key") or kwargs.get("api_key") or "EMPTY",
        domain=kwargs.get("domain", "retail"),
    )


def create_ontology_prompt_agent(tools, domain_policy, **kwargs):
    agent_cls = build_agent_class("ontology_prompt")
    llm_args = kwargs.get("llm_args") or {}
    return agent_cls(
        tools=tools,
        domain_policy=domain_policy,
        llm=kwargs.get("llm") or kwargs.get("agent_llm") or "gemma4-31b",
        llm_args=llm_args,
        base_url=llm_args.get("base_url") or kwargs.get("base_url") or "http://172.16.22.79:9999/v1",
        api_key=llm_args.get("api_key") or kwargs.get("api_key") or "EMPTY",
        domain=kwargs.get("domain", "retail"),
    )


def create_state_only_agent(tools, domain_policy, **kwargs):
    agent_cls = build_agent_class("state_only")
    llm_args = kwargs.get("llm_args") or {}
    return agent_cls(
        tools=tools,
        domain_policy=domain_policy,
        llm=kwargs.get("llm") or kwargs.get("agent_llm") or "gemma4-31b",
        llm_args=llm_args,
        base_url=llm_args.get("base_url") or kwargs.get("base_url") or "http://172.16.22.79:9999/v1",
        api_key=llm_args.get("api_key") or kwargs.get("api_key") or "EMPTY",
        domain=kwargs.get("domain", "retail"),
    )


def create_ontology_lite_agent(tools, domain_policy, **kwargs):
    agent_cls = build_agent_class("ontology_lite")
    llm_args = kwargs.get("llm_args") or {}
    return agent_cls(
        tools=tools,
        domain_policy=domain_policy,
        llm=kwargs.get("llm") or kwargs.get("agent_llm") or "gemma4-31b",
        llm_args=llm_args,
        base_url=llm_args.get("base_url") or kwargs.get("base_url") or "http://172.16.22.79:9999/v1",
        api_key=llm_args.get("api_key") or kwargs.get("api_key") or "EMPTY",
        domain=kwargs.get("domain", "retail"),
    )


def create_typed_admissibility_agent(tools, domain_policy, **kwargs):
    agent_cls = build_agent_class("typed_admissibility")
    llm_args = kwargs.get("llm_args") or {}
    return agent_cls(
        tools=tools,
        domain_policy=domain_policy,
        llm=kwargs.get("llm") or kwargs.get("agent_llm") or "gemma4-31b",
        llm_args=llm_args,
        base_url=llm_args.get("base_url") or kwargs.get("base_url") or "http://172.16.22.79:9999/v1",
        api_key=llm_args.get("api_key") or kwargs.get("api_key") or "EMPTY",
        domain=kwargs.get("domain", "retail"),
    )


def create_schema_baseline_agent(tools, domain_policy, **kwargs):
    agent_cls = build_agent_class("schema")
    llm_args = kwargs.get("llm_args") or {}
    return agent_cls(
        tools=tools,
        domain_policy=domain_policy,
        llm=kwargs.get("llm") or kwargs.get("agent_llm") or "gemma4-31b",
        llm_args=llm_args,
        base_url=llm_args.get("base_url") or kwargs.get("base_url") or "http://172.16.22.79:9999/v1",
        api_key=llm_args.get("api_key") or kwargs.get("api_key") or "EMPTY",
        domain=kwargs.get("domain", "retail"),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run official tau2 with schema or ontology-guided custom agents.")
    parser.add_argument("--domain", default="retail")
    parser.add_argument(
        "--agent-kind",
        choices=[
            "schema",
            "ontology_prompt",
            "state_only",
            "ontology_lite",
            "typed_admissibility",
            "ontology_full",
            "ontology",
        ],
        default="ontology_full",
    )
    parser.add_argument("--agent-model", default="gemma4-31b")
    parser.add_argument("--agent-base-url", default="http://172.16.22.79:9999/v1")
    parser.add_argument("--api-key", default="EMPTY")
    parser.add_argument("--user-llm", required=True, help="User simulator LLM configured for tau2/litellm.")
    parser.add_argument("--user-base-url", default=None, help="Base URL for user simulator LLM (defaults to --agent-base-url).")
    parser.add_argument("--user-api-key", default=None, help="API key for user simulator LLM (defaults to --api-key).")
    parser.add_argument("--num-tasks", type=int, default=None)
    parser.add_argument("--task-ids", nargs="*", default=None)
    parser.add_argument("--task-split-name", default="base")
    parser.add_argument("--num-trials", type=int, default=1)
    parser.add_argument("--max-concurrency", type=int, default=1)
    parser.add_argument("--max-steps", type=int, default=200)
    parser.add_argument("--save-to", default="ontology_guided_tau2")
    args = parser.parse_args()

    # Register GLM models in litellm's model cost map to suppress "model isn't mapped" warnings.
    import litellm as _litellm

    for model_name in {"glm-5.1", "glm-5.2", "GLM-5.1", "GLM-5.2"}:
        if model_name not in _litellm.model_cost:
            _litellm.model_cost[model_name] = {
                "max_tokens": 131072,
                "max_input_tokens": 131072,
                "max_output_tokens": 131072,
                "input_cost_per_token": 0.0,
                "output_cost_per_token": 0.0,
                "litellm_provider": "openai",
            }

    # Override tau2's hardcoded NL assertion evaluator model before any evaluator modules are imported.
    import tau2.config as _tau2_config

    _tau2_config.DEFAULT_LLM_NL_ASSERTIONS = args.user_llm
    _tau2_config.DEFAULT_LLM_NL_ASSERTIONS_ARGS = {
        "temperature": 0.0,
        "base_url": args.user_base_url or args.agent_base_url,
        "api_key": args.user_api_key or args.api_key,
    }

    from tau2.data_model.simulation import TextRunConfig
    from tau2.registry import registry
    from tau2.runner import run_domain

    registry.register_agent_factory(create_schema_baseline_agent, "schema_baseline_agent")
    registry.register_agent_factory(create_ontology_prompt_agent, "ontology_prompt_agent")
    registry.register_agent_factory(create_state_only_agent, "state_only_agent")
    registry.register_agent_factory(create_ontology_lite_agent, "ontology_lite_agent")
    registry.register_agent_factory(
        create_typed_admissibility_agent,
        "typed_admissibility_agent",
    )
    registry.register_agent_factory(create_ontology_guided_agent, "ontology_guided_agent")
    registered_by_kind = {
        "schema": "schema_baseline_agent",
        "ontology_prompt": "ontology_prompt_agent",
        "state_only": "state_only_agent",
        "ontology_lite": "ontology_lite_agent",
        "typed_admissibility": "typed_admissibility_agent",
        "ontology_full": "ontology_guided_agent",
        "ontology": "ontology_guided_agent",
    }
    registered_agent = registered_by_kind[args.agent_kind]
    user_base_url = args.user_base_url or args.agent_base_url
    user_api_key = args.user_api_key or args.api_key
    config = TextRunConfig(
        domain=args.domain,
        agent=registered_agent,
        llm_agent=args.agent_model,
        llm_args_agent={"base_url": args.agent_base_url, "api_key": args.api_key},
        llm_user=args.user_llm,
        llm_args_user={"base_url": user_base_url, "api_key": user_api_key, "temperature": 0.0},
        num_tasks=args.num_tasks,
        task_ids=args.task_ids,
        task_split_name=args.task_split_name,
        num_trials=args.num_trials,
        max_concurrency=args.max_concurrency,
        max_steps=args.max_steps,
        save_to=args.save_to,
    )
    run_domain(config)


if __name__ == "__main__":
    main()
