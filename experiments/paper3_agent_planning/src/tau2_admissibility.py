"""Tau2 action admissibility checks independent of the tau2 runtime.

The official tau2 runner owns dialogue simulation and reward computation. This
module owns the ontology-grounded execution gate: whether a candidate assistant
action is admissible before it is sent to the official tool executor.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

from action_bank import ActionBank


@dataclass(frozen=True)
class ToolCallRecord:
    action: str
    arguments: Dict[str, Any]


class Tau2AdmissibilityChecker:
    """Verify tau2 action candidates against an ontology action layer.

    The checker is intentionally conservative and side-effect free. It checks
    only constraints that can be verified from the candidate, the official tool
    names, the local ActionBank, and already emitted tool calls. Stateful policy
    checks that require tau2 environment internals remain the responsibility of
    the official evaluator and the domain policy.
    """

    def __init__(
        self,
        tool_names: Iterable[str],
        action_bank: Optional[ActionBank] = None,
        enabled: bool = True,
        enforce_conditions: bool = True,
    ):
        self.tool_names: Set[str] = {name for name in tool_names if name}
        self.action_bank = action_bank
        self.enabled = enabled
        self.enforce_conditions = enforce_conditions

    def verify_candidate(
        self,
        candidate: Dict[str, Any],
        history_tool_calls: Sequence[Dict[str, Any] | ToolCallRecord],
        context_text: str = "",
        runtime_state: Any = None,
    ) -> List[str]:
        if not self.enabled:
            return []

        action = str(candidate.get("action", "") or "")
        arguments = candidate.get("arguments", {})
        if not isinstance(arguments, dict):
            arguments = {}
        message_to_user = str(candidate.get("message_to_user", "") or "")

        if action == "respond_to_user":
            return [] if message_to_user else ["COMMUNICATE: respond_to_user requires message_to_user"]

        if action not in self.tool_names:
            return [f"UNKNOWN_ACTION: {action} is not an official tau2 tool"]

        violations: List[str] = []
        schema = self.action_bank.get(action) if self.action_bank is not None else None
        if schema is not None:
            required_parameters = [
                name
                for name in schema.parameters
                if schema.parameter_semantics.get(name, {}).get("required", True)
            ]
            for param_name in required_parameters:
                if param_name not in arguments or arguments.get(param_name) in (None, "", []):
                    violations.append(f"MISSING_PARAMETER: {action}.{param_name}")
            violations.extend(self._check_parameter_types(action, arguments, schema))
            if self.enforce_conditions:
                conditions = schema.preconditions + schema.constraints
                if getattr(schema, "grounding_mode", "strong") == "weak":
                    conditions = _weak_grounding_conditions(conditions)
                elif runtime_state is not None and not runtime_state.target_observed(schema, arguments):
                    binding = schema.target_binding.get("parameter", "target")
                    violations.append(
                        f"GROUNDING: {action}.{binding} is not bound to an observed {schema.target_object}"
                    )
                if runtime_state is not None:
                    violations.extend(
                        self._check_parameter_roles(action, arguments, schema, runtime_state)
                    )
                violations.extend(
                    self._check_schema_conditions(
                        action,
                        arguments,
                        conditions,
                        history_tool_calls,
                        context_text,
                        runtime_state,
                    )
                )
        elif self.action_bank is not None:
            violations.append(f"NOT_IN_ACTION_LAYER: {action} is an official tool but absent from ActionBank")

        if self._is_duplicate(action, arguments, history_tool_calls, runtime_state):
            violations.append(f"DUPLICATE: {action} with same arguments already appeared in history")

        return violations

    def _check_parameter_types(
        self,
        action: str,
        arguments: Dict[str, Any],
        schema: Any,
    ) -> List[str]:
        violations: List[str] = []
        for parameter, semantics in schema.parameter_semantics.items():
            if parameter not in arguments:
                continue
            value = arguments[parameter]
            declared_type = str(semantics.get("type") or "").lower()
            if declared_type.startswith("array") and not isinstance(value, list):
                violations.append(f"PARAMETER_TYPE: {action}.{parameter} must be an array")
            elif declared_type == "object" and not isinstance(value, dict):
                violations.append(f"PARAMETER_TYPE: {action}.{parameter} must be an object")
            elif declared_type in {"string", "enum"} and not isinstance(value, str):
                violations.append(f"PARAMETER_TYPE: {action}.{parameter} must be a string")
            allowed_values = semantics.get("allowed_values") or []
            if allowed_values and value not in allowed_values:
                violations.append(
                    f"PARAMETER_VALUE: {action}.{parameter} must be one of {allowed_values}"
                )
        return violations

    def _is_duplicate(
        self,
        action: str,
        arguments: Dict[str, Any],
        history_tool_calls: Sequence[Dict[str, Any] | ToolCallRecord],
        runtime_state: Any = None,
    ) -> bool:
        if runtime_state is not None:
            return runtime_state.has_successful_call(action, arguments)
        serialized = _stable_json(arguments)
        for previous in history_tool_calls:
            previous_action, previous_arguments = _unpack_tool_call(previous)
            if previous_action != action:
                continue
            if _stable_json(previous_arguments) == serialized:
                return True
        return False

    def _check_schema_conditions(
        self,
        action: str,
        arguments: Dict[str, Any],
        conditions: Sequence[str],
        history_tool_calls: Sequence[Dict[str, Any] | ToolCallRecord],
        context_text: str,
        runtime_state: Any = None,
    ) -> List[str]:
        violations: List[str] = []
        normalized = context_text.lower()
        for condition in conditions:
            condition_text = condition.strip()
            if condition_text == "user_authenticated == true":
                authenticated = (
                    runtime_state.user_authenticated
                    if runtime_state is not None
                    else self._has_authentication_evidence(history_tool_calls, normalized)
                )
                if not authenticated:
                    violations.append(f"AUTHENTICATION_REQUIRED: {action} requires an authenticated user")
                continue
            if condition_text == "user_confirmed == true":
                confirmed = (
                    runtime_state.has_confirmation(action, arguments)
                    if runtime_state is not None
                    else self._has_confirmation_evidence(history_tool_calls, normalized)
                )
                if not confirmed:
                    violations.append(f"CONFIRMATION_REQUIRED: {action} requires explicit user confirmation")
                continue
            if condition_text.startswith("order.status =="):
                expected = _extract_quoted_value(condition_text)
                observed_status = (
                    runtime_state.order_status(arguments.get("order_id"))
                    if runtime_state is not None
                    else ""
                )
                status_matches = (
                    observed_status == expected.lower()
                    if runtime_state is not None
                    else self._has_order_status_evidence(arguments, expected, normalized)
                )
                if expected and not status_matches:
                    order_id = arguments.get("order_id", "<missing>")
                    violations.append(
                        f"ORDER_STATUS_UNVERIFIED: {action} requires order {order_id} status {expected}"
                    )
                continue
            if condition_text.startswith("reason in ["):
                allowed = _extract_allowed_values(condition_text)
                actual = arguments.get("reason")
                if allowed and actual not in allowed:
                    violations.append(f"INVALID_REASON: {action}.reason must be one of {allowed}")
                continue
            if condition_text == "len(item_ids) == len(new_item_ids)":
                item_ids = arguments.get("item_ids")
                new_item_ids = arguments.get("new_item_ids")
                if not isinstance(item_ids, list) or not isinstance(new_item_ids, list) or len(item_ids) != len(new_item_ids):
                    violations.append(f"ITEM_MAPPING_INVALID: {action} requires item_ids and new_item_ids with equal length")
                continue
            if condition_text.startswith("action_taken_on_order"):
                already_taken = (
                    runtime_state.mutation_taken_on_order(arguments.get("order_id"), exclude_action=action)
                    if runtime_state is not None
                    else self._same_order_mutation_already_called(action, arguments, history_tool_calls)
                )
                if already_taken:
                    violations.append(f"ORDER_ACTION_ALREADY_TAKEN: {action} repeats a mutating order action")
                continue
        return violations

    def _check_parameter_roles(
        self,
        action: str,
        arguments: Dict[str, Any],
        schema: Any,
        runtime_state: Any,
    ) -> List[str]:
        violations: List[str] = []
        order_id = arguments.get("order_id")
        source_items: List[str] = []
        replacement_items: List[str] = []
        for parameter, semantics in schema.parameter_semantics.items():
            value = arguments.get(parameter)
            if value in (None, "", []):
                continue
            role = semantics.get("role")
            if role == "source_items":
                source_items = [str(item) for item in value] if isinstance(value, list) else [str(value)]
                missing = [item for item in source_items if item not in runtime_state.order_item_ids(order_id)]
                if missing:
                    violations.append(
                        f"ROLE_BINDING: {action}.{parameter} items are not bound to order {order_id}: {missing}"
                    )
            elif role == "replacement_items":
                replacement_items = [str(item) for item in value] if isinstance(value, list) else [str(value)]
                unknown = [item for item in replacement_items if runtime_state.variant_product_id(item) is None]
                if unknown:
                    violations.append(
                        f"ROLE_BINDING: {action}.{parameter} variants are not observed: {unknown}"
                    )
            elif role == "payment_method":
                valid_methods = runtime_state.valid_payment_method_ids(order_id)
                if str(value) not in valid_methods:
                    violations.append(
                        f"ROLE_BINDING: {action}.{parameter} is not bound to the order or authenticated user"
                    )
        if source_items and replacement_items and len(source_items) == len(replacement_items):
            incompatible = []
            for source_item, replacement_item in zip(source_items, replacement_items):
                source_product = runtime_state.order_item_product(order_id, source_item)
                replacement_product = runtime_state.variant_product_id(replacement_item)
                if not source_product or source_product != replacement_product:
                    incompatible.append((source_item, replacement_item))
            if incompatible:
                violations.append(
                    f"ROLE_BINDING: replacement items must belong to the same product as source items: {incompatible}"
                )
        return violations

    def _has_authentication_evidence(
        self,
        history_tool_calls: Sequence[Dict[str, Any] | ToolCallRecord],
        context_text: str,
    ) -> bool:
        auth_actions = {"find_user_id_by_email", "find_user_id_by_name_zip", "get_user_details"}
        if any(_unpack_tool_call(call)[0] in auth_actions for call in history_tool_calls):
            return True
        return "user_id" in context_text or "authenticated" in context_text

    def _has_confirmation_evidence(
        self,
        history_tool_calls: Sequence[Dict[str, Any] | ToolCallRecord],
        context_text: str,
    ) -> bool:
        if any(_unpack_tool_call(call)[0] == "ask_for_confirmation" for call in history_tool_calls):
            return True
        return _has_explicit_confirmation_text(context_text)

    def _has_order_status_evidence(self, arguments: Dict[str, Any], expected: str, context_text: str) -> bool:
        order_id = str(arguments.get("order_id", "") or "").lower()
        expected_status = expected.lower()
        if not order_id:
            return False
        if order_id not in context_text:
            return False
        if expected_status in context_text:
            return True
        return f"status': '{expected_status}'" in context_text or f'"status": "{expected_status}"' in context_text

    def _same_order_mutation_already_called(
        self,
        action: str,
        arguments: Dict[str, Any],
        history_tool_calls: Sequence[Dict[str, Any] | ToolCallRecord],
    ) -> bool:
        order_id = arguments.get("order_id")
        if not order_id:
            return False
        mutating_prefixes = ("cancel_", "modify_", "return_", "exchange_")
        for previous in history_tool_calls:
            previous_action, previous_arguments = _unpack_tool_call(previous)
            if previous_action == action:
                continue
            if not previous_action.startswith(mutating_prefixes):
                continue
            if previous_arguments.get("order_id") == order_id:
                return True
        return False


def repair_hints(candidate: Dict[str, Any], violations: Sequence[str]) -> List[str]:
    """Translate verifier violations into concrete next-action hints.

    The hints are intentionally operational rather than explanatory. They are
    fed back into the LLM after a rejected candidate to reduce repeated invalid
    proposals and encourage prerequisite-gathering actions.
    """
    action = str(candidate.get("action", "") or "")
    arguments = candidate.get("arguments", {})
    if not isinstance(arguments, dict):
        arguments = {}
    hints: List[str] = []
    for violation in violations:
        if violation.startswith("MISSING_PARAMETER:"):
            missing = violation.split(":", 1)[1].strip()
            hints.append(f"Fill the missing argument `{missing}` from the conversation or ask the user before retrying `{action}`.")
        elif violation.startswith("PARAMETER_TYPE:"):
            hints.append("Use the parameter type declared by the ActionBank role schema.")
        elif violation.startswith("PARAMETER_VALUE:"):
            hints.append("Use one of the values allowed by the ActionBank parameter schema.")
        elif violation.startswith("AUTHENTICATION_REQUIRED:"):
            hints.append("Authenticate the user first, typically with `find_user_id_by_email` or `find_user_id_by_name_zip`, then fetch user details if needed.")
        elif violation.startswith("CONFIRMATION_REQUIRED:"):
            hints.append("Ask the user for explicit confirmation in `message_to_user` before issuing the mutating action.")
        elif violation.startswith("ORDER_STATUS_UNVERIFIED:"):
            order_id = arguments.get("order_id", "the target order")
            hints.append(f"Call `get_order_details` for `{order_id}` and verify the required order status before retrying `{action}`.")
        elif violation.startswith("INVALID_REASON:"):
            hints.append("Use one of the allowed policy reasons from the ActionBank instead of inventing a new reason.")
        elif violation.startswith("ITEM_MAPPING_INVALID:"):
            hints.append("Provide aligned `item_ids` and `new_item_ids` lists with the same length, or ask the user which items to change.")
        elif violation.startswith("DUPLICATE:"):
            hints.append("Do not repeat the same tool call. Use the previous result from the conversation and choose the next needed action.")
        elif violation.startswith("UNKNOWN_ACTION:") or violation.startswith("NOT_IN_ACTION_LAYER:"):
            hints.append("Choose an official tool that appears in the ActionBank; do not invent tool names.")
        elif violation.startswith("COMMUNICATE:"):
            hints.append("If responding to the user, put the user-visible text in `message_to_user`.")
        elif violation.startswith("ORDER_ACTION_ALREADY_TAKEN:"):
            hints.append("Do not perform another mutating action on the same order; finish, communicate the result, or transfer if policy requires.")
        elif violation.startswith("PREMATURE_RESPONSE:"):
            hints.append("Do not end with a generic response while repairable prerequisites remain; take the prerequisite lookup, authentication, confirmation, or parameter-completion action.")
    return _dedupe(hints)


def deterministic_repair_candidate(
    candidate: Dict[str, Any],
    violations: Sequence[str],
    tool_names: Iterable[str],
    context_text: str = "",
    history_tool_calls: Sequence[Dict[str, Any] | ToolCallRecord] = (),
) -> Optional[Dict[str, Any]]:
    """Return a safe prerequisite action for common rejected candidates.

    This intentionally covers only repairs that are directly implied by the
    violation and candidate arguments. It avoids guessing user identifiers or
    missing business parameters.
    """
    available_tools = set(tool_names)
    action = str(candidate.get("action", "") or "")
    arguments = candidate.get("arguments", {})
    if not isinstance(arguments, dict):
        arguments = {}
    violation_types = {_violation_type(v) for v in violations}
    if action in {"find_user_id_by_email", "find_user_id_by_name_zip"}:
        completed = _complete_missing_arguments(candidate, violations, context_text)
        if completed is not None:
            return None if _repair_seen(completed, history_tool_calls) else completed

    if "AUTHENTICATION_REQUIRED" in violation_types and "find_user_id_by_email" in available_tools:
        email = _extract_email(context_text)
        if email:
            repair = {
                "thought": f"Authenticate the user before retrying {action}.",
                "action": "find_user_id_by_email",
                "arguments": {"email": email},
                "message_to_user": "",
                "_repair_for": action,
                "_repair_reason": "AUTHENTICATION_REQUIRED",
            }
            return None if _repair_seen(repair, history_tool_calls) else repair
    if "AUTHENTICATION_REQUIRED" in violation_types and "find_user_id_by_name_zip" in available_tools:
        name_zip = _extract_name_zip(context_text)
        if name_zip:
            repair = {
                "thought": f"Authenticate the user by name and zip before retrying {action}.",
                "action": "find_user_id_by_name_zip",
                "arguments": name_zip,
                "message_to_user": "",
                "_repair_for": action,
                "_repair_reason": "AUTHENTICATION_REQUIRED",
            }
            return None if _repair_seen(repair, history_tool_calls) else repair

    completed = _complete_missing_arguments(candidate, violations, context_text)
    if completed is not None:
        return None if _repair_seen(completed, history_tool_calls) else completed

    if (
        "ORDER_STATUS_UNVERIFIED" in violation_types
        and "AUTHENTICATION_REQUIRED" not in violation_types
        and "get_order_details" in available_tools
        and arguments.get("order_id")
    ):
        repair = {
            "thought": f"Verify order status before retrying {action}.",
            "action": "get_order_details",
            "arguments": {"order_id": arguments["order_id"]},
            "message_to_user": "",
            "_repair_for": action,
            "_repair_reason": "ORDER_STATUS_UNVERIFIED",
        }
        return None if _repair_seen(repair, history_tool_calls) else repair

    if (
        "CONFIRMATION_REQUIRED" in violation_types
        and "AUTHENTICATION_REQUIRED" not in violation_types
        and "ORDER_STATUS_UNVERIFIED" not in violation_types
    ):
        description = _confirmation_description(action, arguments)
        repair = {
            "thought": f"Obtain explicit user confirmation before retrying {action}.",
            "action": "respond_to_user",
            "arguments": {},
            "message_to_user": f"Please confirm that you want me to proceed with: {description}.",
            "_repair_for": action,
            "_repair_arguments": dict(arguments),
            "_repair_reason": "CONFIRMATION_REQUIRED",
        }
        return None if _repair_seen(repair, history_tool_calls) else repair

    return None


def _complete_missing_arguments(
    candidate: Dict[str, Any],
    violations: Sequence[str],
    context_text: str,
) -> Optional[Dict[str, Any]]:
    action = str(candidate.get("action", "") or "")
    arguments = candidate.get("arguments", {})
    if not action or not isinstance(arguments, dict):
        return None
    updated = dict(arguments)
    changed = False
    for violation in violations:
        if not violation.startswith("MISSING_PARAMETER:"):
            continue
        missing = violation.split(":", 1)[1].strip()
        if "." not in missing:
            continue
        _, param_name = missing.rsplit(".", 1)
        if param_name == "email":
            email = _extract_email(context_text)
            if email:
                updated["email"] = email
                changed = True
        elif param_name == "order_id":
            order_id = _extract_unique_order_id(context_text)
            if order_id:
                updated["order_id"] = order_id
                changed = True
        elif param_name in {"first_name", "last_name", "zip"}:
            name_zip = _extract_name_zip(context_text)
            if name_zip and param_name in name_zip:
                updated[param_name] = name_zip[param_name]
                changed = True
    if not changed:
        return None
    return {
        "thought": f"Fill explicit missing arguments for {action} from conversation evidence.",
        "action": action,
        "arguments": updated,
        "message_to_user": str(candidate.get("message_to_user", "") or ""),
        "_repair_for": action,
        "_repair_reason": "MISSING_PARAMETER",
    }


def extract_history_tool_calls(messages: Iterable[Any]) -> List[Dict[str, Any]]:
    """Extract assistant tool calls using duck typing over tau2 message objects."""
    calls: List[Dict[str, Any]] = []
    for message in messages:
        for tool_call in getattr(message, "tool_calls", None) or []:
            name = getattr(tool_call, "name", "")
            arguments = getattr(tool_call, "arguments", {}) or {}
            calls.append({"action": name, "arguments": arguments if isinstance(arguments, dict) else {}})
    return calls


def _unpack_tool_call(record: Dict[str, Any] | ToolCallRecord) -> tuple[str, Dict[str, Any]]:
    if isinstance(record, ToolCallRecord):
        return record.action, record.arguments
    action = str(record.get("action", "") or "")
    arguments = record.get("arguments", {})
    return action, arguments if isinstance(arguments, dict) else {}


def _stable_json(value: Dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)


def _extract_quoted_value(text: str) -> str:
    for quote in ("'", '"'):
        if quote not in text:
            continue
        parts = text.split(quote)
        if len(parts) >= 3:
            return parts[1]
    return ""


def _extract_allowed_values(text: str) -> List[str]:
    if "[" not in text or "]" not in text:
        return []
    body = text.split("[", 1)[1].split("]", 1)[0]
    values = []
    for item in body.split(","):
        value = item.strip().strip("'\"")
        if value:
            values.append(value)
    return values


def _dedupe(items: Iterable[str]) -> List[str]:
    seen = set()
    deduped = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def _violation_type(violation: str) -> str:
    if ":" in violation:
        return violation.split(":", 1)[0]
    return violation.split(" ", 1)[0] if violation else ""


def _weak_grounding_conditions(conditions: Sequence[str]) -> List[str]:
    """Keep policy prerequisites for epistemic actions, drop observed-object checks.

    Epistemic actions acquire state. Requiring the target object to already be
    cached before a read action makes exploration impossible. We keep
    authentication/policy checks and parameter checks, but defer object-status
    and mutation-specific constraints to state-changing actions.
    """
    weak: List[str] = []
    for condition in conditions:
        condition_text = condition.strip()
        if condition_text == "user_authenticated == true":
            weak.append(condition_text)
    return weak


def _confirmation_description(action: str, arguments: Dict[str, Any]) -> str:
    order_id = arguments.get("order_id")
    if order_id:
        return f"{action} for order {order_id}"
    user_id = arguments.get("user_id")
    if user_id:
        return f"{action} for user {user_id}"
    return action


def _repair_seen(repair: Dict[str, Any], history_tool_calls: Sequence[Dict[str, Any] | ToolCallRecord]) -> bool:
    repair_action = str(repair.get("action", "") or "")
    repair_arguments = repair.get("arguments", {})
    if not isinstance(repair_arguments, dict):
        repair_arguments = {}
    for previous in history_tool_calls:
        previous_action, previous_arguments = _unpack_tool_call(previous)
        if previous_action == repair_action and previous_arguments == repair_arguments:
            return True
    return False


def _extract_email(text: str) -> str:
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return match.group(0) if match else ""


def _extract_unique_order_id(text: str) -> str:
    matches = re.findall(r"#[A-Za-z0-9][A-Za-z0-9_-]*", text)
    unique = []
    for match in matches:
        if match not in unique:
            unique.append(match)
    return unique[0] if len(unique) == 1 else ""


def _has_explicit_confirmation_text(text: str) -> bool:
    patterns = (
        r"\bi confirm\b",
        r"\bconfirmed\b",
        r"\bgo ahead\b",
        r"\bplease proceed\b",
        r"\byou may proceed\b",
        r"\bthat is correct\b",
        r"\bsounds good\b",
        r"\byes,\s*(cancel|return|exchange|modify|change|update|proceed)\b",
        r"\byes\s+(please\s+)?(cancel|return|exchange|modify|change|update|proceed)\b",
    )
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _extract_name_zip(text: str) -> Optional[Dict[str, str]]:
    first_name = _extract_labeled_value(text, ("first name", "first_name", "firstname"))
    last_name = _extract_labeled_value(text, ("last name", "last_name", "lastname"))
    zip_code = _extract_labeled_value(text, ("zip code", "zipcode", "zip"))
    if first_name and last_name and zip_code:
        return {"first_name": first_name, "last_name": last_name, "zip": zip_code}
    return None


def _extract_labeled_value(text: str, labels: Sequence[str]) -> str:
    for label in labels:
        pattern = rf"\b{re.escape(label)}\b\s*[:=]\s*([A-Za-z0-9'-]+)"
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return ""
